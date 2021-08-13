from PyQt5.QtWidgets import QTreeView, QAbstractItemView
from PyQt5.QtCore import Qt


class QAnyTreeView(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.draggedItem = None

        self.setDragDropMode(QAbstractItemView.InternalMove)

    def setModel(self, model):
        super().setModel(model)

        # Connect model's rowsMoved signal
        try:
            model.rowsMoved.connect(self.rowsMoved, Qt.UniqueConnection)
        except TypeError:
            pass

    def rowsMoved(self, parent, start, end, destination, row):
        if parent == destination and start < row:
            row -= 1

        index = self.model().index(row, 0, parent)
        self.setCurrentIndex(index)

    def dragEnterEvent(self, e):
        indexes = self.selectedIndexes()
        if indexes:
            self.draggedItem = self.itemFromIndex(indexes[0])

        super().dragEnterEvent(e)

    def dragMoveEvent(self, e):
        if self.draggedItem:
            droppedIndex = self.indexAt(e.pos())
            droppedItem = self.itemFromIndex(droppedIndex)

            # If drop location is invalid or does not share the dragged item's parent
            if not droppedIndex.isValid() or droppedItem.parent != self.draggedItem.parent:
                e.ignore()
                return

            e.accept()

    def dropEvent(self, e):
        if self.draggedItem:
            droppedIndex = self.indexAt(e.pos())
            parentIndex = droppedIndex.parent()

            oldPosition = self.draggedItem.childNumber()
            newPosition = droppedIndex.row()

            self.model().moveRow(parentIndex, oldPosition, parentIndex, newPosition)

    def itemFromIndex(self, index):
        return self.model().getItem(index)
