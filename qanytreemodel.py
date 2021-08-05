from pprint import pprint

from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex, QVariant
from PyQt5.QtWidgets import QUndoStack, QUndoCommand
from anytree.importer import DictImporter

from qanytreeitem import QAnyTreeItem


class QAnyTreeModel(QAbstractItemModel):
    class MoveCommand(QUndoCommand):
        def __init__(self, sourceParent, sourceRow, destinationParent, destinationChild, model, parent=None):
            super().__init__(parent)

            self.sourceParent = sourceParent
            self.sourceRow = sourceRow
            self.destinationParent = destinationParent
            self.destinationChild = destinationChild
            self.model = model

        def undo(self):
            self.model.moveRow(self.destinationParent, self.destinationChild, self.sourceParent, self.sourceRow)
            self.setText('(move item)')

        def redo(self):
            self.model.moveRow(self.sourceParent, self.sourceRow, self.destinationParent, self.destinationChild)
            self.setText('(move item)')

    def __init__(self, data, parent=None):
        super().__init__(parent)

        importer = DictImporter(nodecls=QAnyTreeItem)
        self.root = importer.import_(data)
        self.undoStack = QUndoStack(self)

    ######################
    # Overriden functions
    ######################

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() and parent.column() != 0:
            QModelIndex()

        parentItem = self.getItem(parent)
        if not parentItem:
            return QModelIndex()

        childItem = parentItem.getChild(row)
        if childItem:
            return self.createIndex(row, column, childItem)

        return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = self.getItem(index)
        parentItem = childItem.parent

        if not parentItem or parentItem == self.root:
            return QModelIndex()

        return self.createIndex(parentItem.childNumber(), 0, parentItem)

    def rowCount(self, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if parentItem:
            return parentItem.childCount()

        return 0

    def insertRows(self, position, rows, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if not parentItem:
            return False

        self.beginInsertRows(parent, position, position + rows - 1)
        success = parentItem.insertChildren(position, rows, self.root.columnCount())
        self.endInsertRows()

        return success

    def moveRows(self, sourceParent, sourceRow, count, destinationParent, destinationChild):
        newDestinationChild = destinationChild
        if sourceParent == destinationParent:
            if sourceRow == destinationChild:
                return True
            elif sourceRow < destinationChild:
                newDestinationChild += 1

        destinationItem = self.getItem(destinationParent)
        self.beginMoveRows(sourceParent, sourceRow, sourceRow + count - 1, destinationParent, newDestinationChild)
        for row in range(sourceRow, sourceRow + count):
            index = self.index(row, 0, sourceParent)
            item = self.getItem(index)
            item.parent = destinationItem

            destinationItem.moveChild(item.childNumber(), destinationChild)
        self.endMoveRows()

        return True

    def removeRows(self, position, rows, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if not parentItem:
            return False

        self.beginRemoveRows(parent, position, position + rows - 1)
        success = parentItem.removeChildren(position, rows)
        self.endRemoveRows()

        return success

    def columnCount(self, parent=QModelIndex()):
        return self.root.columnCount()

    def insertColumns(self, position, columns, parent=QModelIndex()):
        self.beginInsertColumns(parent, position, position + columns - 1)
        success = self.root.insertColumns(position, columns)
        self.endInsertColumns()

        return success

    def removeColumns(self, position, columns, parent=QModelIndex()):
        self.beginRemoveColumns(parent, position, position + columns - 1)
        success = self.root.removeColumns(position, columns)
        self.endRemoveColumns()

        if self.root.columnCount() == 0:
            self.removeRows(0, self.rowCount())

        return success

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or (role != Qt.DisplayRole and role != Qt.EditRole):
            return QVariant()

        item = self.getItem(index)

        return item.getData(index.column())

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole:
            return False

        item = self.getItem(index)

        result = item.setData(index.column(), value)
        if result:
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])

        return result

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.root.getData(section)

        return QVariant()

    def setHeaderData(self, section, orientation, value, role=Qt.EditRole):
        if role != Qt.EditRole or orientation != Qt.Horizontal:
            return False

        result = self.root.setData(section, value)
        if result:
            self.headerDataChanged.emit(orientation, section, section)

        return result

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsDropEnabled

        return Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled | Qt.ItemIsEditable | super().flags(index)

    def supportedDropActions(self):
        return Qt.MoveAction

    ##################
    # Helper functions
    ##################

    def copyRow(self, sourceParent, sourceRow, destinationParent, destinationChild):
        columns = self.columnCount()
        for column in range(columns):
            destination_index = self.index(destinationChild, column, destinationParent)
            source_index = self.index(sourceRow, column, sourceParent)
            self.setData(destination_index, self.data(source_index))

    def createMoveCommand(self, sourceParent, sourceRow, destinationParent, destinationChild):
        move_command = self.MoveCommand(sourceParent, sourceRow, destinationParent, destinationChild, self)
        self.undoStack.push(move_command)

    def getItem(self, index):
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self.root

    def toDict(self):
        return self.root.toDict()
