import sys
import qdarktheme
from threads import *
from port import Port
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
import pyqtgraph 


class GraphApp(QApplication):
    def __init__(self, argv):
        super().__init__(argv)

        self.window = GraphWindow()
        self.window.show()

        self.exec()


class GraphWindow(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.threadpool = QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

        grid = QGridLayout()
        self.create_widgets(grid)

        stylesheet = qdarktheme.load_stylesheet("dark")
        self.setStyleSheet(stylesheet)

        self.setWindowTitle("Oscilloscope Simulator")
        self.resize(1200, 1000)

    def create_widgets(self, grid):

        self.rx_box = GraphPort(name="Channel 1", parent=self)
        self.tx_box = GraphPort(name="Channel 2", parent=self)

        grid.addWidget(self.tx_box, 0, 0)
        grid.addWidget(self.rx_box, 0, 1)

        self.rx_graph, self.rx_graph_line, self.rx_x, self.rx_y = self.create_graph("Channel 1", True)
        self.tx_graph, self.tx_graph_line, self.tx_x, self.tx_y = self.create_graph("Channel 2", False)

        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_out_button = QPushButton("Zoom Out")

        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button.clicked.connect(self.zoom_out)

        grid.addWidget(self.rx_graph, 2, 0, 2, 2)
        grid.addWidget(self.tx_graph, 4, 0, 2, 2)
        grid.addWidget(self.zoom_in_button, 6, 0)
        grid.addWidget(self.zoom_out_button, 6, 1)
        self.setLayout(grid)

    def create_graph(self, name, rx):
        graph = pyqtgraph.PlotWidget()
        graph.setBackground("black")
        pen = pyqtgraph.mkPen(color=(0, 0, 255), width=0)
        graph.setTitle(f"{name} Graph", color="w", size="10pt")
        styles = {"color": "w", "font-size": "10px"}
        graph.setLabel("left", "Bit", **styles)
        graph.setLabel("bottom", "Time", **styles)
        graph.addLegend()
        graph.showGrid(x=True, y=True)

        x = [0] * 40 if rx else [0] * 20
        y = [0] * 40 if rx else [0] * 20
        graph.setYRange(0, 1.5)
        # Get a line reference
        line = graph.plot(
            x,
            y,
            name="Raw Bit",
            symbol="o",
            pen=pen
        )

        return graph, line, x, y

    def zoom_out(self):
        add = [0, 0]

        self.rx_x = add + add + self.rx_x
        self.rx_y = add + add + self.rx_y
        self.tx_x = add + self.tx_x
        self.tx_y = add + self.tx_y

    def zoom_in(self):
        self.rx_x = self.rx_x[4:]
        self.rx_y = self.rx_y[4:]
        self.tx_x = self.tx_x[2:]
        self.tx_y = self.tx_y[2:]

    def update_graph(self, new_bit, name):
        if name == "Ground Rx":
            self.rx_x = self.rx_x[2:]
            self.rx_y = self.rx_y[2:]
            # self.rx_x = self.rx_x[1:]
            # self.rx_y = self.rx_y[1:]
            x, y = self.rx_x, self.rx_y
            line = self.rx_graph_line
        else:
            self.tx_x = self.tx_x[2:]
            self.tx_y = self.tx_y[2:]
            # self.tx_x = self.tx_x[1:]
            # self.tx_y = self.tx_y[1:]
            x, y = self.tx_x, self.tx_y
            line = self.tx_graph_line

        new_time = x[-1] + 1
        last_bit = y[-1]

        x.append(new_time)
        x.append(new_time)

        y.append(last_bit)
        y.append(new_bit)
        line.setData(x, y)


class GraphPort(Port):
    def __init__(self, name, parent=None):
        Port.__init__(self, name=name, updates_map=False, parent=parent)

    # Overwrite the data sending part
    def read_from_port(self) -> str:

        data = self.port.readAll()

        if len(data) > 0:
            # Convert data to string and remove all NULL characters (else prints weird)
            data_str = data.toStdString().replace(chr(0), "")

            # Send to terminal
            terminal_window = self.parent.port_terminal
            terminal = terminal_window.terminals[self.name]  # terminals is a name-to-terminal dict
            terminal.insertPlainText(data_str)
            terminal.moveCursor(QTextCursor.End)  # automates scrolling like PuTTY

            for i in data_str:
                bit = int(i)
                if (bit == 0 or bit == 1):
                    self.parent.update_graph(bit, self.name)
            return data


if __name__ == "__main__":
    app = GraphApp(sys.argv)
