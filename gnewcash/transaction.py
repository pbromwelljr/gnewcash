from datetime import datetime
from xml.etree import ElementTree

from guid_object import GuidObject


class Transaction(GuidObject):
    """
    Represents a transaction in GnuCash.
    """
    def __init__(self):
        super(Transaction, self).__init__()
        self.currency = None
        self.date_posted = None
        self.date_entered = None
        self.description = ''
        self.splits = []
        self.memo = None

    def __str__(self):
        return '{} - {}'.format(self.date_posted.strftime('%m/%d/%Y'), self.description)

    def __repr__(self):
        return str(self)

    @property
    def as_xml(self):
        """
        Returns the current transaction as GnuCash-compatible XML

        :return: ElementTree.Element object
        """
        date_format = '%Y-%m-%d 00:00:00 %z'
        timestamp_format = '%Y-%m-%d %H:%M:%S %z'

        transaction_node = ElementTree.Element('gnc:transaction', {'version': '2.0.0'})
        ElementTree.SubElement(transaction_node, 'trn:id', {'type': 'guid'}).text = self.guid

        transaction_node.append(self.currency.as_short_xml('trn:currency'))

        date_posted_node = ElementTree.SubElement(transaction_node, 'trn:date-posted')
        ElementTree.SubElement(date_posted_node, 'ts:date').text = datetime.strftime(self.date_posted, date_format)
        date_entered_node = ElementTree.SubElement(transaction_node, 'trn:date-entered')
        ElementTree.SubElement(date_entered_node, 'ts:date').text = datetime.strftime(self.date_entered,
                                                                                      timestamp_format)
        ElementTree.SubElement(transaction_node, 'trn:description').text = self.description

        if self.memo:
            ElementTree.SubElement(transaction_node, 'trn:num').text = self.memo

        if self.splits:
            splits_node = ElementTree.SubElement(transaction_node, 'trn:splits')
            for split in self.splits:
                splits_node.append(split.as_xml)

        return transaction_node

    def __lt__(self, other):
        return self.date_posted < other.date_posted

    def __eq__(self, other):
        return self.date_posted == other.date_posted

    @property
    def cleared(self):
        """
        Checks if all splits in the transaction are cleared.

        :return: Boolean indicating if all splits in the transaction are cleared.
        :rtype: bool
        """
        return sum([1 for split in self.splits if split.reconciled_state.lower() == 'c']) > 0

    def mark_transaction_cleared(self):
        """
        Marks all splits in the transaction as cleared (reconciled_state = 'c')
        """
        for split in self.splits:
            split.reconciled_state = 'c'


class Split(GuidObject):
    """
    Represents a split in GnuCash.
    """
    def __init__(self, account, amount, reconciled_state='n'):
        super(Split, self).__init__()
        self.reconciled_state = reconciled_state
        self.amount = amount
        self.account = account

    def __str__(self):
        return '{} - {}'.format(self.account, str(self.amount))

    def __repr__(self):
        return str(self)

    @property
    def as_xml(self):
        """
        Returns the current split as GnuCash-compatible XML

        :return: ElementTree.Element object
        """
        split_node = ElementTree.Element('trn:split')
        ElementTree.SubElement(split_node, 'split:id', {'type': 'guid'}).text = self.guid
        ElementTree.SubElement(split_node, 'split:reconciled-state').text = self.reconciled_state
        ElementTree.SubElement(split_node, 'split:value').text = str(int(self.amount * 100)) + '/100'
        ElementTree.SubElement(split_node, 'split:quantity').text = str(int(self.amount * 100)) + '/100'
        ElementTree.SubElement(split_node, 'split:account', {'type': 'guid'}).text = self.account.guid
        return split_node


class TransactionManager:
    """
    Class used to add/remove transactions while maintaining a chronological order based on transaction posted date.
    """
    def __init__(self):
        self.transactions = list()

    def add(self, new_transaction):
        """
        Adds a transaction to the transaction manager

        :param new_transaction: Transaction to add
        :type: Transaction
        """
        # Inserting transactions in order
        for index, transaction in enumerate(self.transactions):
            if transaction.date_posted > new_transaction.date_posted:
                self.transactions.insert(index, new_transaction)
                break
            elif transaction.date_posted == new_transaction.date_posted and transaction.amount < new_transaction.amount:
                self.transactions.insert(index, new_transaction)
                break
        else:
            self.transactions.append(new_transaction)

    def delete(self, transaction):
        """
        Removes a transaction from the transaction manager

        :param transaction: Transaction to remove
        :type: Transaction
        """
        # We're looking up by GUID here because a simple list remove doesn't work
        for index, iter_transaction in enumerate(self.transactions):
            if iter_transaction.guid == transaction.guid:
                del self.transactions[index]
                break

    def get_transactions(self, *, from_account=None, to_account=None):
        """
        Generator function that gets transactions based on a from account and/or to account for the transaction

        :param from_account:
        :param to_account:
        :return: Generator that produces transactions based on the given from account and/or to account
        :rtype: Iterator[Transaction]
        """
        for transaction in self.transactions:
            if transaction.from_account == from_account or transaction.to_account == to_account:
                yield transaction

    def get_account_starting_balance(self, account):
        """
        Retrieves the starting balance for the provided account given the list of transactions in the manager.

        :param account: Account to get the starting balance for
        :type: Account
        :return: Account starting balance
        """
        return account.get_starting_balance(list(self.get_transactions(from_account=account,
                                                                       to_account=account)))

    def get_account_ending_balance(self, account):
        """
        Retrieves the ending balance for the provided account given the list of transactions in the manager.

        :param account: Account to get the ending balance for
        :type: Account
        :return: Account starting balance
        """
        return account.get_ending_balance(list(self.get_transactions(from_account=account,
                                                                     to_account=account)))

    def minimum_balance_past_date(self, account, date):
        """
        Retrieves the minimum balance past a certain date for the given account.

        :param account: Account to get the minimum balance for
        :type account: Account
        :param date: datetime object representing the date you want to find the minimum balance for.
        :type date: datetime.datetime
        :return: Tuple containing the minimum balance (element 0) and the date it's at that balance (element 1)
        """
        return account.minimum_balance_past_date(self, date)

    def get_balance_at_date(self, account, date):
        """
        Retrieves the account balance for the specified account at a certain date.
        If the provided date is None, it will retrieve the ending balance.

        :param account: List of transactions or TransactionManager
        :type account: Account
        :param date: Last date to consider when determining the account balance.
        :type date: datetime.datetime
        :return: Account balance at specified date (or ending balance) or 0, if no applicable transactions were found.
        """
        return account.get_balance_at_date(self, date)

    # Making TransactionManager iterable
    def __getitem__(self, item):
        if item > len(self):
            raise IndexError
        return self.transactions[item]

    def __len__(self):
        return len(self.transactions)

    def __eq__(self, other):
        for my_transaction, other_transaction in zip(self.transactions, other.transactions):
            if my_transaction != other_transaction:
                return False
        return True
