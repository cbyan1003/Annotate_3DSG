from PyQt6 import QtWidgets, QtGui, QtCore
import open3d as o3d
import sys
import threading
import time
import io
import re
import json
import os
import subprocess
from PyQt6.QtCore import QTimer,QThread, pyqtSlot
from time import sleep
from PyQt6.QtWidgets import QFileDialog
import logging

logging.basicConfig(
    level=logging.DEBUG, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  
        logging.FileHandler("app.log") 
    ]
)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        logging.info("Initializing MainWindow")
        self.selected_points_lineedit1 = None
        self.selected_points_lineedit2 = None
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QGridLayout(widget)
        self.setCentralWidget(widget)
        self.selected_points_list = []
        self.selected_points = str()
        
        self.file_path = None
        self.pcd = None
        self.vis = None
        self.window_id = None
        self.json_data =None
        
        btn_select_file = QtWidgets.QPushButton("Select Point Cloud")
        btn_select_file.clicked.connect(self.select_point_cloud_file)
        layout.addWidget(btn_select_file, 0, 0)
        
        btn_select_file2 = QtWidgets.QPushButton("Close Point Cloud")
        btn_select_file2.clicked.connect(self.close_vis)
        layout.addWidget(btn_select_file2, 0, 1)
        
        btn1 = QtWidgets.QPushButton("Select instance1")
        btn1.clicked.connect(self.show_selected_points1)
        layout.addWidget(btn1, 4, 0)
        
        btn2 = QtWidgets.QPushButton("Select instance2")
        btn2.clicked.connect(self.show_selected_points2)
        layout.addWidget(btn2, 5, 0)

        btn3 = QtWidgets.QPushButton("Add a relationship")
        btn3.clicked.connect(self.add_relationship)
        layout.addWidget(btn3, 6, 3)
        
        # # 创建QLineEdit控件
        self.selected_points_lineedit1 = QtWidgets.QLineEdit()
        self.selected_points_id_lineedit1 = QtWidgets.QLineEdit()
        self.selected_points_label_lineedit1 = QtWidgets.QLineEdit()
        self.selected_points_lineedit1.setReadOnly(True)
        layout.addWidget(self.selected_points_lineedit1, 4, 1)
        layout.addWidget(self.selected_points_id_lineedit1, 4, 2)
        layout.addWidget(self.selected_points_label_lineedit1, 4, 3)
        self.selected_points_lineedit2 = QtWidgets.QLineEdit()
        self.selected_points_id_lineedit2 = QtWidgets.QLineEdit()
        self.selected_points_label_lineedit2 = QtWidgets.QLineEdit()
        self.selected_points_lineedit2.setReadOnly(True)
        layout.addWidget(self.selected_points_lineedit2, 5, 1)
        layout.addWidget(self.selected_points_id_lineedit2, 5, 2)
        layout.addWidget(self.selected_points_label_lineedit2, 5, 3)
        self.relationship_id_lineedit = QtWidgets.QLineEdit()
        layout.addWidget(self.relationship_id_lineedit, 6, 2)
        

        # # 重定向标准输出
        # self.redirector = OutputRedirector(self.selected_points_lineedit1)
        # sys.stdout = self.redirector
        # self.redirector = OutputRedirector(self.selected_points_lineedit2)
        # sys.stdout = self.redirector

        # # QLineEdit内容每次改变，都会根据选取的点输出id和label
        self.selected_points_lineedit1.textChanged.connect(self.show_id_label1)
        self.selected_points_lineedit2.textChanged.connect(self.show_id_label2)
        
        # # 构建QComboBox控件
        self.cb = QtWidgets.QComboBox()
        self.RelationshipDict = {'supported by': 1, 'left': 2, 'right': 3, 'front': 4, 'behind': 5,
                     'close by': 6, 'inside': 7, 'bigger than': 8, 'smaller than': 9, 'higher than': 10,
                     'lower than': 11, 'same symmetry as': 12, 'same as': 13, 'attached to': 14, 'standing on': 15,
                     'lying on': 16, 'hanging on': 17, 'connected to': 18, 'leaning against': 19, 'part of': 20,
                     'belonging to': 21, 'build in': 22, 'standing in': 23, 'cover': 24, 'lying in': 25,
                     'hanging in': 26, 'same color': 27, 'same material': 28, 'same texture': 29, 'same shape': 30,
                     'same state': 31, 'same object type': 32, 'messier than': 33, 'cleaner than': 34, 'fuller than': 35,
                     'more closed': 36, 'more open': 37, 'brighter than': 38, 'darker than': 39, 'more comfortable than': 40}
        
        self.cb.addItems(self.RelationshipDict.keys())
        self.cb.setCurrentIndex(-1)
        self.cb.currentTextChanged.connect(self.typeChanged)
        layout.addWidget(self.cb, 6, 0, 1, 2)

    def select_point_cloud_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Point Cloud File", "", "PLY Files (*.ply);;All Files (*)")
        if file_path:
            self.file_path = os.path.dirname(file_path)
            self.load_json(os.path.join(self.file_path, "segments_anno.json"))
            self.load_pcd(file_path)
    
    def load_json(self, anno_file_path):
        with open(anno_file_path, 'r', encoding='utf-8') as file:
            json_content = file.read()
        self.json_data = json.loads(json_content)
        sceneid = self.json_data["sceneId"]
        logging.info(f"SceneId:{sceneid}, Json loaded")
    
    def close_vis(self):
        if self.vis != None:
            self.vis.destroy_window()
            self.timer.stop()
    
    def load_pcd(self, file_path):
        self.pcd = o3d.io.read_point_cloud(file_path)
        print(f"Loaded point cloud with {len(self.pcd.points)} points.")
        self.vis = o3d.visualization.VisualizerWithEditing()
        self.vis.create_window(visible=True)
        self.window_id = self.find_window("Open3D - free view")
        self.vis.destroy_window()
        
        self.vis = o3d.visualization.VisualizerWithEditing()
        self.vis.create_window(visible=False)
        if self.window_id:
            self.window_id = int(self.window_id, 16) 
            print(self.window_id)
            self.window = QtGui.QWindow.fromWinId(self.window_id)
            self.windowcontainer = self.createWindowContainer(self.window, self.centralWidget())
            self.centralWidget().layout().addWidget(self.windowcontainer, 1, 0, 2, 4)
        else:
            print("can not get window_id")
        self.vis.add_geometry(self.pcd)
        
        sceneid = self.json_data["sceneId"]
        logging.info(f"SceneId:{sceneid}, pcd loaded")
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run)
        self.timer.start(100) 
    
    def run(self):
        self.vis.run()
        self.selected_points_list=self.vis.get_picked_points()
        if len(self.selected_points_list) != 0:
            self.selected_points = str(self.selected_points_list[0])
        print(self.selected_points_list)
        print(self.selected_points)
        
    def find_window(self, title):
        try:
            output = subprocess.check_output(['wmctrl', '-l']).decode('utf-8')
            for line in output.splitlines():
                if title in line:
                    window_id = line.split()[0]  # 窗口ID通常在行的开头
                    logging.debug(f"Find window: {window_id}")
                    return window_id
        except Exception as e:
            logging.error(f"Error finding window: {e}")
        return None
        
    def show_selected_points1(self):
        self.selected_points_lineedit1.setText(self.selected_points)
        
    def show_selected_points2(self):
        self.selected_points_lineedit2.setText(self.selected_points)

    def show_id_label1(self, value):
        lineedit_content = value
        point_id = lineedit_content

        for seg_group in self.json_data["segGroups"]:
            for segment in seg_group["segments"]:
                if str(segment) == point_id:  # 比较字符串以匹配数字串
                    self.selected_points_id_lineedit1.setText(f"id: {seg_group['id']}")
                    self.selected_points_label_lineedit1.setText(f"label: {seg_group['label']}")
                    break
    
    def show_id_label2(self, value):
        lineedit_content = value
        point_id = lineedit_content
        
        for seg_group in self.json_data["segGroups"]:
            for segment in seg_group["segments"]:
                if str(segment) == point_id:  # 比较字符串以匹配数字串
                    self.selected_points_id_lineedit2.setText(f"id: {seg_group['id']}")
                    self.selected_points_label_lineedit2.setText(f"label: {seg_group['label']}")

    def typeChanged(self, text):
        self.relationship_id_lineedit.setText(f"rel id: {self.RelationshipDict.get(text)}")

    def add_relationship(self):
        # 提取QLineEdit的内容
        instance1_id = self.selected_points_id_lineedit1.text()
        instance2_id = self.selected_points_id_lineedit2.text()
        relationship_id = self.relationship_id_lineedit.text()
        relationship_text = self.cb.currentText()

        sceneId = self.json_data["sceneId"]
        
        relationship_tuple = [int(instance1_id.strip().split(': ')[1]), int(instance2_id.strip().split(': ')[1]), int(relationship_id.strip().split(': ')[1]), relationship_text]

        if int(instance1_id.strip().split(': ')[1]) != 31 and int(instance2_id.strip().split(': ')[1]) != 31:
            self.write_to_json(relationship_tuple)

    def write_to_json(self, relationship_tuple):
        file_path = "/home/mint/annotate/anno.json"
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
            
        data.append(relationship_tuple)
        
        with open(file_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)
            
        logging.debug(f"write Relation: {relationship_tuple}")
        
    def closeEvent(self, event):
        self.vis.destroy_window()
        event.accept()

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    form = MainWindow()
    form.setWindowTitle('Annotate relationships')
    form.setGeometry(100, 100, 600, 500)
    form.show()
    logging.info("Application started")
    sys.exit(app.exec())