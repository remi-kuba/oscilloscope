from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from PySide6.QtSerialPort import *
from threads import *


class Port(QGroupBox):

    def __init__(self, name: str, updates_map: bool, parent=None):

        self.name = name
        self.parent = parent
        self.byte_array = ""
        super().__init__(f"{self.name} Setup", parent)  # Set name of the box to given f string
        # Boolean whether terminal should parse messages and update map with new coordinates
        self.update_map = updates_map

        self.baudrate_list = [
            "1200",
            "2400",
            "4800",
            "9600",
            "19200",
            "38400",
            "57600",
            "115200",
        ]
        self.default_baudrate_idx = self.baudrate_list.index("9600")

        self.port_list = QSerialPortInfo().availablePorts()
        self.port_names = [port.portName() for port in self.port_list]
        # Create empty port instance
        self.port = QSerialPort()

        # Set connected (green) and disconnected (red) symbol
        self.green_symbol = QPixmap("icons/green_button.png")
        self.green_symbol.setDevicePixelRatio(55)  # make symbols smaller
        self.red_symbol = QPixmap("icons/red_button.png")
        self.red_symbol.setDevicePixelRatio(55)

        self.format_box()

    def format_box(self):

        self.f_box = QFormLayout()

        self.create_boxes()

        self.f_box.addRow("Serial COM Port", self.port_box)
        self.f_box.addRow("Baud Rate", self.baudrate_box)
        self.f_box.addRow("Status", self.status_bar)
        self.f_box.addRow(self.connect_button)

        self.setLayout(self.f_box)

    def create_boxes(self):

        self.create_port_box()
        self.create_baudrate_box()
        self.create_status_bar()
        self.create_connect_button()

    def create_port_box(self):

        self.port_box = QComboBox(placeholderText="Port Number")
        self.port_box.view().setMinimumWidth(120)

        # Add all available serial ports can connect to
        self.port_box.addItems(self.port_names)

    def create_baudrate_box(self):

        self.baudrate_box = QComboBox()

        # Add all common baud rates in dropdown list of baud rate box
        self.baudrate_box.addItems(self.baudrate_list)

        # Set default baud rate (shown without dropdown)
        self.baudrate_box.setCurrentIndex(self.default_baudrate_idx)

        # Allow user to type in unique baud rate
        # Set valid baud rate range to [1, 999999]
        self.baudrate_box.setEditable(True)
        valid_range = QIntValidator()
        valid_range.setRange(1, 999999)
        self.baudrate_box.setValidator(valid_range)

    def create_status_bar(self):

        self.status_bar = QHBoxLayout()

        # Default is not connected
        self.status_symbol = QLabel()
        self.status_symbol.setPixmap(self.red_symbol)
        self.status_text = QLabel()
        self.status_text.setText("Not Connected")

        self.status_bar.addWidget(self.status_symbol)
        self.status_bar.addWidget(self.status_text)
        # left align the status symbol + text (can't use addStretch because
        #   expanding GUI only expands left side)
        for _ in range(5):
            self.status_bar.addWidget(QLabel())

    def create_connect_button(self):

        self.connect_button = QPushButton("Connect Port")
        self.connect_button.setCheckable(True)
        # Once connect button is pressed, call link_port method and try connect to specified port
        self.connect_button.clicked.connect(self.link_port)

    def link_port(self):

        # Read inputs
        current_port = self.port_box.currentText()
        current_baud = int(self.baudrate_box.currentText())

        if self.connect_button.isChecked():  # Must connect to a port

            error = self.connect_port(current_port, current_baud)

            if error:

                self.show_error(error)  # Print error on GUI

                # Allow for next click to try connect to port again
                self.connect_button.setChecked(False)

            else:

                self.show_connection()

                # Dictionary of k = terminal name (on tab bar), v = terminal output text
                terminals = self.parent.port_terminal.terminals
                # Tab widget holding all terminals
                tab_bar = self.parent.port_terminal.tab_bar
                # Find index of terminal with the name given to this setup widget (i.e., either Air Tx or Gnd Rx)
                terminal_idx = tab_bar.indexOf(terminals[self.name])
                # Once connected, switch to current terminal to view output
                tab_bar.setCurrentIndex(terminal_idx)

        else:  # Must disconnect to the current port

            self.disconnect_port()

    def connect_port(self, port_name: str, baud: int) -> Exception:

        # Check that user-selected port in available ports
        port_idx = self.port_names.index(port_name) if port_name in self.port_names else None

        if not port_idx:
            if not port_name:  # Only true when port input box has not been selected
                return NameError("Must Select A Port To Connect To")
            else:
                return NameError("Chosen Port No Longer Available")
        else:
            port_info = self.port_list[port_idx]

        self.port.setPort(port_info)
        self.port.setBaudRate(baud)
        # PuTTY configurations
        self.port.setDataBits(QSerialPort.DataBits(8))
        self.port.setStopBits(QSerialPort.StopBits(1))
        self.port.setParity(QSerialPort.Parity.NoParity)
        self.port.setFlowControl(QSerialPort.FlowControl.NoFlowControl)

        # Start reading port data
        # TODO: Check if it's actually multi-threaded
        self.worker = Worker(self.read_from_port)
        self.parent.threadpool.start(self.worker)

        self.port.readyRead.connect(self.read_from_port)

        # Open port if not connected anywhere else
        port_open = self.port.open(QIODevice.ReadWrite)
        error = ConnectionError("Port Already In Use")

        return None if port_open else error

    def disconnect_port(self):

        if self.port.isOpen():
            self.port.close()

        self.show_disconnection()

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

            # Update the map if user wants
            if self.update_map:
                self.parent.map.update_map(data_str)

            return data

    def show_connection(self):

        self.connect_button.setText("Disconnect Port")
        self.status_symbol.setPixmap(self.green_symbol)
        self.status_text.setText("Connected")

    def show_error(self, error):

        self.status_text.setText(str(error))

    def show_disconnection(self):

        self.connect_button.setText("Connect Port")
        self.status_symbol.setPixmap(self.red_symbol)
        self.status_text.setText("Not Connected")


def make_text():

    text = QTextEdit("")
    text.setReadOnly(True)

    return text

