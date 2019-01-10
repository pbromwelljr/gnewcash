"""
.. module:: transaction
   :synopsis:
.. moduleauthor: Paul Bromwell Jr.
"""

from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree

from gnewcash.commodity import Commodity
from gnewcash.guid_object import GuidObject
from gnewcash.slot import Slot


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
        self.slots = []
        self.memo = None

    def __str__(self):
        return '{} - {}'.format(self.date_posted.strftime('%m/%d/%Y'), self.description)

    def __repr__(self):
        return str(self)

    @property
    def as_xml(self):
        """
        Returns the current transaction as GnuCash-compatible XML

        :return: Current transaction as XML
        :rtype: xml.etree.ElementTree.Element
        """
        timestamp_format = '%Y-%m-%d %H:%M:%S %z'

        transaction_node = ElementTree.Element('gnc:transaction', {'version': '2.0.0'})
        ElementTree.SubElement(transaction_node, 'trn:id', {'type': 'guid'}).text = self.guid

        if self.currency:
            transaction_node.append(self.currency.as_short_xml('trn:currency'))

        if self.memo:
            ElementTree.SubElement(transaction_node, 'trn:num').text = self.memo

        date_posted_node = ElementTree.SubElement(transaction_node, 'trn:date-posted')
        ElementTree.SubElement(date_posted_node, 'ts:date').text = datetime.strftime(self.date_posted, timestamp_format)
        date_entered_node = ElementTree.SubElement(transaction_node, 'trn:date-entered')
        ElementTree.SubElement(date_entered_node, 'ts:date').text = datetime.strftime(self.date_entered,
                                                                                      timestamp_format)
        ElementTree.SubElement(transaction_node, 'trn:description').text = self.description

        if self.slots:
            slots_node = ElementTree.SubElement(transaction_node, 'trn:slots')
            for slot in self.slots:
                slots_node.append(slot.as_xml)

        if self.splits:
            splits_node = ElementTree.SubElement(transaction_node, 'trn:splits')
            for split in self.splits:
                splits_node.append(split.as_xml)

        return transaction_node

    @classmethod
    def from_xml(cls, transaction_node, namespaces, account_objects):
        """
        Creates a Transaction object from the GnuCash XML

        :param transaction_node: XML node for the transaction
        :type transaction_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param account_objects: Account objects already created from XML (used for assigning accounts)
        :type account_objects: list[Account]
        :return: Transaction object from XML
        :rtype: Transaction
        """
        transaction = cls()
        transaction.guid = transaction_node.find('trn:id', namespaces).text
        date_entered = transaction_node.find('trn:date-entered', namespaces).find('ts:date', namespaces).text
        date_posted = transaction_node.find('trn:date-posted', namespaces).find('ts:date', namespaces).text
        transaction.date_entered = datetime.strptime(date_entered, '%Y-%m-%d %H:%M:%S %z')
        transaction.date_posted = datetime.strptime(date_posted, '%Y-%m-%d %H:%M:%S %z')
        transaction.description = transaction_node.find('trn:description', namespaces).text

        memo = transaction_node.find('trn:num', namespaces)
        if memo is not None:
            transaction.memo = memo.text

        currency_node = transaction_node.find('trn:currency', namespaces)
        if currency_node is not None:
            transaction.currency = Commodity(currency_node.find('cmdty:id', namespaces).text,
                                             currency_node.find('cmdty:space', namespaces).text)

        slots = transaction_node.find('trn:slots', namespaces)
        if slots:
            for slot in slots.findall('slot', namespaces):
                transaction.slots.append(Slot.from_xml(slot, namespaces))

        splits = transaction_node.find('trn:splits', namespaces)
        for split in list(splits):
            transaction.splits.append(Split.from_xml(split, namespaces, account_objects))

        return transaction

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
        self.action = None
        self.memo = None
        self.quantity_denominator = '100'

    def __str__(self):
        return '{} - {}'.format(self.account, str(self.amount))

    def __repr__(self):
        return str(self)

    @property
    def as_xml(self):
        """
        Returns the current split as GnuCash-compatible XML

        :return: Current split as XML
        :rtype: xml.etree.ElementTree.Element
        """
        split_node = ElementTree.Element('trn:split')
        ElementTree.SubElement(split_node, 'split:id', {'type': 'guid'}).text = self.guid

        if self.memo:
            ElementTree.SubElement(split_node, 'split:memo').text = self.memo
        if self.action:
            ElementTree.SubElement(split_node, 'split:action').text = self.action

        ElementTree.SubElement(split_node, 'split:reconciled-state').text = self.reconciled_state
        ElementTree.SubElement(split_node, 'split:value').text = str(int(self.amount * 100)) + '/100'
        ElementTree.SubElement(split_node, 'split:quantity').text = '/'.join([
            str(int(self.amount * 100)), self.quantity_denominator])
        ElementTree.SubElement(split_node, 'split:account', {'type': 'guid'}).text = self.account.guid
        return split_node

    @classmethod
    def from_xml(cls, split_node, namespaces, account_objects):
        """
        Creates an Split object from the GnuCash XML

        :param split_node: XML node for the split
        :type split_node: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param account_objects: Account objects already created from XML (used for assigning parent account)
        :type account_objects: list[Account]
        :return: Split object from XML
        :rtype: Split
        """
        account = split_node.find('split:account', namespaces).text

        value = split_node.find('split:value', namespaces).text
        value = Decimal(value[:value.find('/')]) / Decimal(100)

        new_split = cls([x for x in account_objects if x.guid == account][0],
                        value, split_node.find('split:reconciled-state', namespaces).text)
        new_split.guid = split_node.find('split:id', namespaces).text

        split_memo = split_node.find('split:memo', namespaces)
        if split_memo is not None:
            new_split.memo = split_memo.text

        split_action = split_node.find('split:action', namespaces)
        if split_action is not None:
            new_split.action = split_action.text

        quantity_node = split_node.find('split:quantity', namespaces)
        if quantity_node is not None:
            quantity = quantity_node.text
            if '/' in quantity:
                new_split.quantity_denominator = quantity.split('/')[1]

        return new_split


class TransactionManager:
    """
    Class used to add/remove transactions while maintaining a chronological order based on transaction posted date.
    """
    def __init__(self):
        self.transactions = list()
        self.disable_sort = False

    def add(self, new_transaction):
        """
        Adds a transaction to the transaction manager

        :param new_transaction: Transaction to add
        :type new_transaction: Transaction
        """
        if not self.disable_sort:
            # Inserting transactions in order
            for index, transaction in enumerate(self.transactions):
                if transaction.date_posted > new_transaction.date_posted:
                    self.transactions.insert(index, new_transaction)
                    break
                elif transaction.date_posted == new_transaction.date_posted:
                    self.transactions.insert(index, new_transaction)
                    break
            else:
                self.transactions.append(new_transaction)
        else:
            self.transactions.append(new_transaction)

    def delete(self, transaction):
        """
        Removes a transaction from the transaction manager

        :param transaction: Transaction to remove
        :type transaction: Transaction
        """
        # We're looking up by GUID here because a simple list remove doesn't work
        for index, iter_transaction in enumerate(self.transactions):
            if iter_transaction.guid == transaction.guid:
                del self.transactions[index]
                break

    def get_transactions(self, account=None):
        """
        Generator function that gets transactions based on a from account and/or to account for the transaction

        :param account: Account to retrieve transactions for (default None, all transactions)
        :type account: Account
        :return: Generator that produces transactions based on the given from account and/or to account
        :rtype: Iterator[Transaction]
        """
        for transaction in self.transactions:
            if account is None or account in list(map(lambda x: x.account, transaction.splits)):
                yield transaction

    def get_account_starting_balance(self, account):
        """
        Retrieves the starting balance for the provided account given the list of transactions in the manager.

        :param account: Account to get the starting balance for
        :type account: Account
        :return: Account starting balance
        :rtype: decimal.Decimal
        """
        return account.get_starting_balance(list(self.get_transactions(account)))

    def get_account_ending_balance(self, account):
        """
        Retrieves the ending balance for the provided account given the list of transactions in the manager.

        :param account: Account to get the ending balance for
        :type account: Account
        :return: Account starting balance
        :rtype: decimal.Decimal
        """
        return account.get_ending_balance(list(self.get_transactions(account)))

    def minimum_balance_past_date(self, account, date):
        """
        Retrieves the minimum balance past a certain date for the given account.

        :param account: Account to get the minimum balance for
        :type account: Account
        :param date: datetime object representing the date you want to find the minimum balance for.
        :type date: datetime.datetime
        :return: Tuple containing the minimum balance (element 0) and the date it's at that balance (element 1)
        :rtype: tuple
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
        :rtype: decimal.Decimal or int
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


class ScheduledTransaction(GuidObject):
    """
    Class that represents a scheduled transaction in Gnucash.
    """
    def __init__(self):
        super(ScheduledTransaction, self).__init__()
        self.name = None
        self.enabled = False
        self.auto_create = False
        self.auto_create_notify = False
        self.advance_create_days = -1
        self.advance_remind_days = -1
        self.instance_count = 0
        self.start_date = None
        self.last_date = None
        self.end_date = None
        self.template_account = None
        self.recurrence_multiplier = 0
        self.recurrence_period = None
        self.recurrence_start = None

    @property
    def as_xml(self):
        """
        Returns the current scheduled transaction as GnuCash-compatible XML

        :return: Current scheduled transaction as XML
        :rtype: xml.etree.ElementTree.Element
        """
        xml_node = ElementTree.Element('gnc:schedxaction', attrib={'version': '2.0.0'})
        if self.guid:
            ElementTree.SubElement(xml_node, 'sx:id', attrib={'type': 'guid'}).text = self.guid
        if self.name:
            ElementTree.SubElement(xml_node, 'sx:name').text = self.name
        ElementTree.SubElement(xml_node, 'sx:enabled').text = 'y' if self.enabled else 'n'
        ElementTree.SubElement(xml_node, 'sx:autoCreate').text = 'y' if self.auto_create else 'n'
        ElementTree.SubElement(xml_node, 'sx:autoCreateNotify').text = 'y' if self.auto_create_notify else 'n'
        if self.advance_create_days is not None:
            ElementTree.SubElement(xml_node, 'sx:advanceCreateDays').text = str(self.advance_create_days)
        if self.advance_remind_days is not None:
            ElementTree.SubElement(xml_node, 'sx:advanceRemindDays').text = str(self.advance_remind_days)
        if self.instance_count is not None:
            ElementTree.SubElement(xml_node, 'sx:instanceCount').text = str(self.instance_count)
        if self.start_date:
            start_node = ElementTree.SubElement(xml_node, 'sx:start')
            ElementTree.SubElement(start_node, 'gdate').text = self.start_date.strftime('%Y-%m-%d')
        if self.last_date:
            last_node = ElementTree.SubElement(xml_node, 'sx:last')
            ElementTree.SubElement(last_node, 'gdate').text = self.last_date.strftime('%Y-%m-%d')
        if self.end_date:
            end_node = ElementTree.SubElement(xml_node, 'sx:end')
            ElementTree.SubElement(end_node, 'gdate').text = self.end_date.strftime('%Y-%m-%d')
        if self.template_account:
            ElementTree.SubElement(xml_node, 'sx:templ-acct', attrib={'type': 'guid'}).text = self.template_account.guid
        if self.recurrence_multiplier is not None or self.recurrence_period is not None \
                or self.recurrence_start is not None:
            schedule_node = ElementTree.SubElement(xml_node, 'sx:schedule')
            recurrence_node = ElementTree.SubElement(schedule_node, 'gnc:recurrence', attrib={'version': '1.0.0'})
            if self.recurrence_multiplier:
                ElementTree.SubElement(recurrence_node, 'recurrence:mult').text = str(self.recurrence_multiplier)
            if self.recurrence_period:
                ElementTree.SubElement(recurrence_node, 'recurrence:period_type').text = self.recurrence_period
            if self.recurrence_start:
                start_node = ElementTree.SubElement(recurrence_node, 'recurrence:start')
                ElementTree.SubElement(start_node, 'gdate').text = self.recurrence_start.strftime('%Y-%m-%d')
        return xml_node

    @classmethod
    def from_xml(cls, xml_obj, namespaces, template_account_root):
        """
        Creates a ScheduledTransaction object from the GnuCash XML

        :param xml_obj: XML node for the scheduled transaction
        :type xml_obj: ElementTree.Element
        :param namespaces: XML namespaces for GnuCash elements
        :type namespaces: dict[str, str]
        :param template_account_root: Root template account
        :type template_account_root: Account
        :return: ScheduledTransaction object from XML
        :rtype: ScheduledTransaction
        """
        new_obj = cls()
        new_obj.guid = cls.read_xml_child_text(xml_obj, 'sx:id', namespaces)
        new_obj.name = cls.read_xml_child_text(xml_obj, 'sx:name', namespaces)
        new_obj.enabled = cls.read_xml_child_boolean(xml_obj, 'sx:enabled', namespaces)
        new_obj.auto_create = cls.read_xml_child_boolean(xml_obj, 'sx:autoCreate', namespaces)
        new_obj.auto_create_notify = cls.read_xml_child_boolean(xml_obj, 'sx:autoCreateNotify', namespaces)
        new_obj.advance_create_days = cls.read_xml_child_int(xml_obj, 'sx:advanceCreateDays', namespaces)
        new_obj.advance_remind_days = cls.read_xml_child_int(xml_obj, 'sx:advanceRemindDays', namespaces)
        new_obj.instance_count = cls.read_xml_child_int(xml_obj, 'sx:instanceCount', namespaces)
        new_obj.start_date = cls.read_xml_child_date(xml_obj, 'sx:start', namespaces)
        new_obj.last_date = cls.read_xml_child_date(xml_obj, 'sx:last', namespaces)
        new_obj.end_date = cls.read_xml_child_date(xml_obj, 'sx:end', namespaces)

        template_account_node = xml_obj.find('sx:templ-acct', namespaces)
        if template_account_node is not None:
            new_obj.template_account = template_account_root.get_subaccount_by_id(template_account_node.text)

        schedule_node = xml_obj.find('sx:schedule', namespaces)
        if schedule_node is not None:
            recurrence_node = schedule_node.find('gnc:recurrence', namespaces)
            if recurrence_node is not None:
                new_obj.recurrence_multiplier = cls.read_xml_child_int(
                    recurrence_node, 'recurrence:mult', namespaces
                )
                new_obj.recurrence_period = cls.read_xml_child_text(
                    recurrence_node, 'recurrence:period_type', namespaces)
                new_obj.recurrence_start = cls.read_xml_child_date(
                    recurrence_node, 'recurrence:start', namespaces)

        return new_obj

    @classmethod
    def read_xml_child_text(cls, xml_object, tag_name, namespaces):
        """
        Reads the text from a specific child XML element

        :param xml_object: Current XML object
        :type xml_object: ElementTree.Element
        :param tag_name: Child tag name
        :type tag_name: str
        :param namespaces: GnuCash namespaces
        :type namespaces: dict[str, str]
        :return: Child node's text
        :rtype: str
        """
        target_node = xml_object.find(tag_name, namespaces)
        if target_node is not None:
            return target_node.text
        return None

    @classmethod
    def read_xml_child_boolean(cls, xml_object, tag_name, namespaces):
        """
        Reads the text from a specific child XML element and returns a Boolean if the text is "Y" or "y"

        :param xml_object: Current XML object
        :type xml_object: ElementTree.Element
        :param tag_name: Child tag name
        :type tag_name: str
        :param namespaces: GnuCash namespaces
        :type namespaces: dict[str, str]
        :return: True if child node's text is "Y" or "Y", otherwise False.
        :rtype: bool
        """
        node_text = cls.read_xml_child_text(xml_object, tag_name, namespaces)
        if node_text and node_text.lower() == 'y':
            return True
        if node_text:
            return False
        return None

    @classmethod
    def read_xml_child_int(cls, xml_object, tag_name, namespaces):
        """
        Reads the text from a specific child XML element and returns its text as an integer value.

        :param xml_object: Current XML object
        :type xml_object: ElementTree.Element
        :param tag_name: Child tag name
        :type tag_name: str
        :param namespaces: GnuCash namespaces
        :type namespaces: dict[str, str]
        :return: Child's text as an integer value
        :rtype: int
        """
        node_text = cls.read_xml_child_text(xml_object, tag_name, namespaces)
        if node_text:
            return int(node_text)
        return None

    @classmethod
    def read_xml_child_date(cls, xml_object, tag_name, namespaces):
        """
        Reads the text from a specific child XML element and returns its inner gdate text as a datetime.

        :param xml_object: Current XML object
        :type xml_object: ElementTree.Element
        :param tag_name: Child tag name
        :type tag_name: str
        :param namespaces: GnuCash namespaces
        :type namespaces: dict[str, str]
        :return: Child's gdate's text as datetime
        :rtype: datetime.datetime
        """
        target_node = xml_object.find(tag_name, namespaces)
        if target_node is None:
            return None

        date_node = target_node.find('gdate', namespaces)
        if date_node is None:
            return None

        return datetime.strptime(date_node.text, '%Y-%m-%d') if date_node.text else None
