from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex, QVariant
from PyQt5.QtWidgets import QUndoStack, QUndoCommand
from anytree.importer import DictImporter

from .qanytreeitem import QAnyTreeItem


class QAnyTreeModel(QAbstractItemModel):
    def __init__(self, data, parent=None):
        super().__init__(parent)

        importer = DictImporter(nodecls=QAnyTreeItem)
        self.root = importer.import_(data)
        self.undoStack = QUndoStack(self)

    ######################
    # Overridden functions
    ######################

    def index(self, row, column, parent=QModelIndex()):
        if parent.isValid() and parent.column() != 0:
            return QModelIndex()

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
        addCommand = AddCommand(position, rows, parent, self)
        self.undoStack.push(addCommand)

        return addCommand.result

    def _insertRows(self, position, rows, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if not parentItem:
            return False

        self.beginInsertRows(parent, position, position + rows - 1)
        success = parentItem.insertChildren(position, rows, self.root.columnCount())
        self.endInsertRows()

        return success

    def moveRows(self, sourceParent, sourceRow, count, destinationParent, destinationChild):
        moveCommand = self.MoveCommand(sourceParent, sourceRow, count, destinationParent, destinationChild, self)
        self.undoStack.push(moveCommand)

        return moveCommand.result

    def _moveRows(self, sourceParent, sourceRow, count, destinationParent, destinationChild):
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
        deleteCommand = DeleteCommand(position, rows, parent, self)
        self.undoStack.push(deleteCommand)

        return deleteCommand.result

    def _removeRows(self, position, rows, parent=QModelIndex()):
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
        modifyCommand = ModifyCommand(oldValue, value, index, self)
        self.undoStack.push(modifyCommand)

        return modifyCommand.result

    def _setData(self, index, value):
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

    def getItem(self, index):
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self.root

    def toDict(self):
        return self.root.toDict()


class MoveCommand(QUndoCommand):
    def __init__(self, sourceParent, sourceRow, count, destinationParent, destinationChild, model, parent=None):
        super().__init__(parent)

        self.sourceParent = sourceParent
        self.sourceRow = sourceRow
        self.count = count
        self.destinationParent = destinationParent
        self.destinationChild = destinationChild
        self.model = model

        self.result = False

        self.setText('(move item)')

    def undo(self):
        self.result = self.model._moveRows(self.destinationParent, self.destinationChild, self.count, self.sourceParent,
                                           self.sourceRow)

    def redo(self):
        self.result = self.model._moveRows(self.sourceParent, self.sourceRow, self.count, self.destinationParent,
                                           self.destinationChild)


class AddCommand(QUndoCommand):
    def __init__(self, position, rows, parent, model):
        super().__init__()

        self.position = position
        self.rows = rows
        self.parent = parent
        self.model = model

        self.result = False

        if rows > 1:
            self.setText('(add item)')
        else:
            self.setText('(add items)')

    def undo(self):
        self.result = self.model._removeRows(self.position, self.rows, self.parent)

    def redo(self):
        self.result = self.model._insertRows(self.position, self.rows, self.parent)


class DeleteCommand(QUndoCommand):
    def __init__(self, position, rows, parent, model):
        super().__init__()

        self.position = position
        self.rows = rows
        self.parent = parent
        self.model = model

        self.indexLocations = getIndexLocations(parent)

        self.result = False

        # Backup data from deleted items
        self.data = []
        for row in range(rows):
            index = model.index(position + row, 0, parent)
            item = model.getItem(index)
            self.data.append(item.toDict())

        if rows > 1:
            self.setText('(delete items)')
        else:
            self.setText('(delete item)')

    def undo(self):
        importer = DictImporter(nodecls=QAnyTreeItem)
        parent = getIndexFromLocations(self.indexLocations, self.model)
        parentItem = self.model.getItem(parent)

        self.result = self.model.beginInsertRows(parent, self.position, self.position + self.rows - 1)
        for row, data in enumerate(self.data):
            print(data)
            item = importer.import_(data)

            # Reconstruct branch
            item.parent = parentItem
            parentItem.moveChild(parentItem.childCount() - 1, self.position + row)

        self.model.endInsertRows()

    def redo(self):
        parent = getIndexFromLocations(self.indexLocations, self.model)
        self.result = self.model._removeRows(self.position, self.rows, parent)


class ModifyCommand(QUndoCommand):
    def __init__(self, oldValue, newValue, index, model):
        super().__init__()

        self.oldValue = oldValue
        self.newValue = newValue
        self.index = index
        self.model = model

        self.indexLocations = getIndexLocations(index)
        self.result = False

        self.setText('(modify item)')

    def undo(self):
        index = getIndexFromLocations(self.indexLocations, self.model)
        self.result = self.model._setData(index, self.oldValue)

    def redo(self):
        index = getIndexFromLocations(self.indexLocations, self.model)
        self.result = self.model._setData(index, self.newValue)


def getIndexFromLocations(indexLocations, model, parent=QModelIndex()):
    index = QModelIndex()
    for row, column in indexLocations:
        index = model.index(row, column, parent)
        parent = index

    return index


def getIndexLocations(index):
    indexLocations = []
    while index.row() != -1:
        indexLocations.append((index.row(), index.column()))
        index = index.parent()

    indexLocations.reverse()

    return indexLocations
