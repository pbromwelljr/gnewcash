from datetime import datetime
from xml.etree import ElementTree

from gnewcash.guid_object import GuidObject


class Transaction(GuidObject):
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
        return sum([1 for split in self.splits if split.reconciled_state.lower() == 'c']) > 0

    def mark_transaction_cleared(self):
        for split in self.splits:
            split.reconciled_state = 'c'


class Split(GuidObject):
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
        split_node = ElementTree.Element('trn:split')
        ElementTree.SubElement(split_node, 'split:id', {'type': 'guid'}).text = self.guid
        ElementTree.SubElement(split_node, 'split:reconciled-state').text = self.reconciled_state
        ElementTree.SubElement(split_node, 'split:value').text = str(int(self.amount * 100)) + '/100'
        ElementTree.SubElement(split_node, 'split:quantity').text = str(int(self.amount * 100)) + '/100'
        ElementTree.SubElement(split_node, 'split:account', {'type': 'guid'}).text = self.account.guid
        return split_node


class TransactionManager:
    def __init__(self):
        self.transactions = list()

    def add(self, new_transaction) -> None:
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
        # We're looking up by GUID here because a simple list remove doesn't work
        for index, iter_transaction in enumerate(self.transactions):
            if iter_transaction.guid == transaction.guid:
                del self.transactions[index]
                break

    def get_transactions(self, *, from_account=None, to_account=None):
        for transaction in self.transactions:
            if transaction.from_account == from_account or transaction.to_account == to_account:
                yield transaction

    def get_account_starting_balance(self, account):
        return account.get_starting_balance(list(self.get_transactions(from_account=account,
                                                                       to_account=account)))

    def get_account_ending_balance(self, account):
        return account.get_ending_balance(list(self.get_transactions(from_account=account,
                                                                     to_account=account)))

    def minimum_balance_past_date(self, account, date):
        return account.minimum_balance_past_date(self, date)

    def get_balance_at_date(self, account, date):
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
