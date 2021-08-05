# qanytree

qanytree is an anytree-based implementation of QTreeView and QAbstractItemModel for PyQt5 supporting dynamic reordering, importing from and exporting to dictionary, undo/redo and more.

## Requirements
```
anytree~=2.8
PyQt5~=5.15
```

## Usage
`QAnyTreeView` subclasses `PyQt5.QtWidgets.QTreeView` and `QAnyTreeModel` subclasses `PyQt5.QtCore.QAbstractItemModel`. Simply add a `QAnyTree` widget to your GUI and set its model to an instance to `QAnyTreeModel`.

## Example
```python
import sys

from PyQt5.QtWidgets import QMainWindow, QApplication
from qanytree import QAnyTreeModel, QAnyTreeView


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        data = {
            'data': ['Key', 'Value'],
            'children': [{
                'data': [1, 'A'],
            }, {
                'data': [2, 'B'],
                'children': [{
                    'data': [3, 'C']
                }]
            }]
        }

        model = QAnyTreeModel(data)
        view = QAnyTreeView()
        view.setModel(model)

        self.setCentralWidget(view)


app = QApplication(sys.argv)
mainWindow = MainWindow()
mainWindow.show()

sys.exit(app.exec())
```