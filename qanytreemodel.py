from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex, QVariant
from PyQt5.QtWidgets import QUndoStack, QUndoCommand
from anytree.importer import DictImporter

from .qanytreeitem import QAnyTreeItem


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

    class AddCommand(QUndoCommand):
        def __init__(self, row, index, model, parent=None):
            super().__init__(parent)

            self.row = row
            self.index = index
            self.model = model

        def undo(self):
            self.model.removeRow(self.row, self.index)
            self.setText('(add item)')

        def redo(self):
            self.model.insertRow(self.row, self.index)
            self.setText('(add item)')

    class DeleteCommand(QUndoCommand):
        def __init__(self, row, index, model, parent=None):
            super().__init__(parent)

            self.row = row
            self.model = model

            self.parent = model.parent(index)
            self.item = model.getItem(index)
            self.data = None

        def undo(self):
            # Import data into tree
            importer = DictImporter(nodecls=QAnyTreeItem)
            item = importer.import_(self.data)

            # Reconstruct branch
            self.model.beginInsertRows(self.parent, self.row, self.row)
            item.parent = self.model.getItem(self.parent)
            self.model.endInsertRows()

            self.setText('(delete item)')

        def redo(self):
            self.data = self.item.toDict()
            self.model.removeRow(self.row, self.parent)
            self.setText('(delete item)')

    class ModifyCommand(QUndoCommand):
        def __init__(self, oldValue, newValue, index, model, parent=None):
            super().__init__(parent)

            self.oldValue = oldValue
            self.newValue = newValue
            self.index = index
            self.model = model

            self.result = False

        def undo(self):
            self.result = self.model.setData_(self.index, self.oldValue)
            self.setText('(modify item)')

        def redo(self):
            self.result = self.model.setData_(self.index, self.newValue)
            self.setText('(modify item)')

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

        oldValue = self.data(index, role)
        modifyCommand = self.ModifyCommand(oldValue, value, index, self)
        self.undoStack.push(modifyCommand)

        return modifyCommand.result

    def setData_(self, index, value):
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
            destinationIndex = self.index(destinationChild, column, destinationParent)
            sourceIndex = self.index(sourceRow, column, sourceParent)
            self.setData(destinationIndex, self.data(sourceIndex))

    def createMoveCommand(self, sourceParent, sourceRow, destinationParent, destinationChild):
        moveCommand = self.MoveCommand(sourceParent, sourceRow, destinationParent, destinationChild, self)
        self.undoStack.push(moveCommand)

    def createAddCommand(self, row, index):
        addCommand = self.AddCommand(row, index, self)
        self.undoStack.push(addCommand)

    def createDeleteCommand(self, row, index):
        deleteCommand = self.DeleteCommand(row, index, self)
        self.undoStack.push(deleteCommand)

    def getItem(self, index):
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self.root

    def toDict(self):
        return self.root.toDict()
