from PyQt5.QtCore import QVariant
from anytree import NodeMixin
from anytree.exporter import DictExporter


class QAnyTreeItem(NodeMixin):
    def __init__(self, data, parent=None, children=None):
        self.data = data
        self.parent = parent
        if children:
            self.children = children

    def getData(self, column):
        if 0 <= column < len(self.data):
            return self.data[column]

        return QVariant()

    def setData(self, column, value):
        if 0 <= column < len(self.data):
            self.data[column] = value
            return True

        return False

    def getChild(self, index):
        if 0 <= index < len(self.children):
            return self.children[index]

        return None

    def childNumber(self):
        if self.parent:
            return self.parent.children.index(self)

        return 0

    def childCount(self):
        return len(self.children)

    def appendChild(self, data):
        child = QAnyTreeItem(data=data, parent=self)
        return True

    def moveChild(self, fromIndex, toIndex):
        children = list(self.children)
        children.insert(toIndex, children.pop(fromIndex))
        self.children = children

    def insertChildren(self, position, count, columns):
        if 0 <= position <= len(self.children):
            # Copy current list of children
            children = list(self.children)

            # Insert new items
            for _ in range(count):
                data = [None] * columns
                item = QAnyTreeItem(data, self)
                children.insert(position, item)

            # Set children to modified list
            self.children = children

            return True

        return False

    def removeChildren(self, position, count):
        if 0 <= position + count <= len(self.children):
            for row in range(count - 1, -1, -1):
                self.children[position + row].parent = None

            return True

        return False

    def columnCount(self):
        return len(self.data)

    def insertColumns(self, position, columns):
        if 0 <= position <= len(self.data):
            for column in range(columns):
                self.data.insert(position, QVariant())

            for child in self.children:
                child.insertColumns(position, columns)

            return True

        return False

    def removeColumns(self, position, columns):
        if 0 <= position <= len(self.data):
            for column in range(columns):
                self.data.pop(position)

            for child in self.children:
                child.removeColumns(position, columns)

            return True

        return False

    def toDict(self):
        exporter = DictExporter()
        return exporter.export(self)
