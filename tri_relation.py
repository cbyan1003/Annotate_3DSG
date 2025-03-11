from PyQt6 import QtWidgets, QtGui, QtCore
from PyQt6.QtCore import Qt
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
from PyQt6.QtWidgets import QFileDialog, QApplication
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
        self.all_rels = dict()
        
        btn_select_file = QtWidgets.QPushButton("Select Point Cloud")
        btn_select_file.clicked.connect(self.select_point_cloud_file)
        layout.addWidget(btn_select_file, 0, 1)
        
        btn_select_file2 = QtWidgets.QPushButton("Save Anno && Close Point Cloud")
        btn_select_file2.clicked.connect(self.close_vis)
        layout.addWidget(btn_select_file2, 0, 2)
        
        self.label = QtWidgets.QLabel("已标注关系: 0", self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label, 0, 0)
        
        self.label2 = QtWidgets.QLabel("已标注主语: 0", self)
        self.label2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label2, 1, 0)
        
        self.label3 = QtWidgets.QLabel("已标注宾语: 0", self)
        self.label3.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label3, 2, 0)
        
        self.txttimer = QTimer(self)
        self.txttimer.timeout.connect(self.update_text)
        
        btn1 = QtWidgets.QPushButton("Select 主语")
        btn1.clicked.connect(self.show_selected_points1)
        layout.addWidget(btn1, 4, 0)
        
        btn2 = QtWidgets.QPushButton("Select 宾语")
        btn2.clicked.connect(self.show_selected_points2)
        layout.addWidget(btn2, 5, 0)

        btn3 = QtWidgets.QPushButton("Add a relationship")
        btn3.clicked.connect(self.add_relationship)
        layout.addWidget(btn3, 6, 3, 2, 1)
        
        # # 创建QLineEdit控件
        self.selected_points_lineedit1 = QtWidgets.QLineEdit()
        self.selected_points_id_lineedit1 = QtWidgets.QLineEdit()
        self.selected_points_label_lineedit1 = QtWidgets.QLineEdit()
        self.selected_points_lineedit1.setReadOnly(True)
        self.selected_points_id_lineedit1.setReadOnly(True)
        self.selected_points_label_lineedit1.setReadOnly(True)
        layout.addWidget(self.selected_points_lineedit1, 4, 1)
        layout.addWidget(self.selected_points_id_lineedit1, 4, 2)
        layout.addWidget(self.selected_points_label_lineedit1, 4, 3)
        self.selected_points_lineedit2 = QtWidgets.QLineEdit()
        self.selected_points_id_lineedit2 = QtWidgets.QLineEdit()
        self.selected_points_label_lineedit2 = QtWidgets.QLineEdit()
        self.selected_points_lineedit2.setReadOnly(True)
        self.selected_points_id_lineedit2.setReadOnly(True)
        self.selected_points_label_lineedit2.setReadOnly(True)
        layout.addWidget(self.selected_points_lineedit2, 5, 1)
        layout.addWidget(self.selected_points_id_lineedit2, 5, 2)
        layout.addWidget(self.selected_points_label_lineedit2, 5, 3)
        
        self.sup_relationship_id_lineedit = QtWidgets.QLineEdit()
        self.sup_relationship_id_lineedit.setReadOnly(True)
        layout.addWidget(self.sup_relationship_id_lineedit, 7, 0)
        
        self.pxm_relationship_id_lineedit = QtWidgets.QLineEdit()
        self.pxm_relationship_id_lineedit.setReadOnly(True)
        layout.addWidget(self.pxm_relationship_id_lineedit, 7, 1)

        
        self.cmp_relationship_id_lineedit = QtWidgets.QLineEdit()
        self.cmp_relationship_id_lineedit.setReadOnly(True)
        layout.addWidget(self.cmp_relationship_id_lineedit, 7, 2)

        # # QLineEdit内容每次改变，都会根据选取的点输出id和label
        self.selected_points_lineedit1.textChanged.connect(self.show_id_label1)
        self.selected_points_lineedit2.textChanged.connect(self.show_id_label2)
        
        # # 构建QComboBox控件
        self.sup_cb = QtWidgets.QComboBox()
        self.sup_RelationshipDict = {'None': None, 'supported by': 1, 'attached to': 2, 'standing on': 3,
                     'lying on': 4, 'hanging on': 5, 'connected to': 6, 'leaning against': 7, 'part of': 8,
                     'belonging to': 9, 'build in': 10, 'standing in': 11, 'cover': 12, 'lying in': 13,
                     'hanging in': 14}
        
        self.sup_cb.addItems(self.sup_RelationshipDict.keys())
        self.sup_cb.setCurrentIndex(-1)
        self.sup_cb.currentTextChanged.connect(self.sup_typeChanged)
        layout.addWidget(self.sup_cb, 6, 0, 1, 1)
        
        self.pxm_cb = QtWidgets.QComboBox()
        self.pxm_RelationshipDict = {'None': None, 'left': 15, 'right': 16, 'front': 17, 'behind': 18,
                     'close by': 19, 'inside': 20}
        
        self.pxm_cb.addItems(self.pxm_RelationshipDict.keys())
        self.pxm_cb.setCurrentIndex(-1)
        self.pxm_cb.currentTextChanged.connect(self.pxm_typeChanged)
        layout.addWidget(self.pxm_cb, 6, 1, 1, 1)
        
        self.cmp_cb = QtWidgets.QComboBox()
        self.cmp_RelationshipDict = {'None': None, 'bigger than': 21, 'smaller than': 22, 'higher than': 23, 'lower than': 24, 'same symmetry as': 25, 'same as': 26,
                                     'same color': 27, 'same material': 28, 'same texture': 29, 'same shape': 30,
                     'same state': 31, 'same object type': 32, 'messier than': 33, 'cleaner than': 34, 'fuller than': 35,
                     'more closed': 36, 'more open': 37, 'brighter than': 38, 'darker than': 39, 'more comfortable than': 40, 'closer to': 41, 'futher from': 42}
        
        self.cmp_cb.addItems(self.cmp_RelationshipDict.keys())
        self.cmp_cb.setCurrentIndex(-1)
        self.cmp_cb.currentTextChanged.connect(self.cmp_typeChanged)
        layout.addWidget(self.cmp_cb, 6, 2, 1, 1)

    def update_text(self):
        count = len(self.all_rels['sup_Rel']) + len(self.all_rels['pxm_Rel']) + len(self.all_rels['cmp_Rel'])
        self.label.setText(f"已标注关系: {count}")
        count2 = 0
        count3 = 0
        if count != 0:
            sup_first_elements = {triplet[0] for triplet in self.all_rels['sup_Rel']}
            pxm_first_elements = {triplet[0] for triplet in self.all_rels['pxm_Rel']}
            cmp_first_elements = {triplet[0] for triplet in self.all_rels['cmp_Rel']}
            
            sup_third_elements = {triplet[1] for triplet in self.all_rels['sup_Rel']}
            pxm_third_elements = {triplet[1] for triplet in self.all_rels['pxm_Rel']}
            cmp_third_elements = {triplet[1] for triplet in self.all_rels['cmp_Rel']}

            all_unique_first_elements = sup_first_elements | pxm_first_elements | cmp_first_elements
            all_unique_third_elements = sup_third_elements | pxm_third_elements | cmp_third_elements

            unique_first_count = len(all_unique_first_elements)
            unique_third_count = len(all_unique_third_elements)
            
            count2 = unique_first_count
            count3 = unique_third_count
        self.label2.setText(f"已标注主语: {count2}")
        self.label3.setText(f"已标注宾语: {count3}")
    
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
            self.txttimer.stop()
            self.write_to_json(self.all_rels)
            self.all_rels.clear()
            self.clear_all_button()
            
    def clear_all_button(self):
        self.label.setText(f"已标注关系: 0")
        self.label2.setText(f"已标注主语: 0")
        self.label3.setText(f"已标注宾语: 0")
        
        self.selected_points_lineedit1.setText("")
        self.selected_points_lineedit2.setText("")
        
        self.sup_cb.currentTextChanged.disconnect(self.sup_typeChanged)
        self.pxm_cb.currentTextChanged.disconnect(self.pxm_typeChanged)
        self.cmp_cb.currentTextChanged.disconnect(self.cmp_typeChanged)
        
        self.sup_relationship_id_lineedit.setText("")
        self.pxm_relationship_id_lineedit.setText("")
        self.cmp_relationship_id_lineedit.setText("")
        self.selected_points_id_lineedit1.setText("")
        self.selected_points_id_lineedit2.setText("")
        self.selected_points_label_lineedit1.setText("")
        self.selected_points_label_lineedit2.setText("")
        self.sup_cb.setCurrentIndex(-1)
        self.pxm_cb.setCurrentIndex(-1)
        self.cmp_cb.setCurrentIndex(-1)
        
        self.sup_cb.currentTextChanged.connect(self.sup_typeChanged)
        self.pxm_cb.currentTextChanged.connect(self.pxm_typeChanged)
        self.cmp_cb.currentTextChanged.connect(self.cmp_typeChanged)
        
        
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
            self.centralWidget().layout().addWidget(self.windowcontainer, 1, 1, 2, 4)
        else:
            print("can not get window_id")
        self.vis.add_geometry(self.pcd)
        
        sceneid = self.json_data["sceneId"]
        self.all_rels['SceneId'] = sceneid
        self.all_rels['sup_Rel'] = []
        self.all_rels['pxm_Rel'] = []
        self.all_rels['cmp_Rel'] = []
        logging.info(f"SceneId:{sceneid}, pcd loaded")
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.run)
        self.timer.start(10) 
        self.txttimer.start(1000)
    
    def run(self):
        self.vis.run()
        self.selected_points_list=self.vis.get_picked_points()
        if len(self.selected_points_list) != 0:
            self.selected_points = str(self.selected_points_list[0])
            logging.debug(f"selected_points:{self.selected_points}")

    
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

    def sup_typeChanged(self, text):
        self.sup_relationship_id_lineedit.setText(f"sup_rel id: {self.sup_RelationshipDict.get(text)}")
    
    def pxm_typeChanged(self, text):
        self.pxm_relationship_id_lineedit.setText(f"pxm_rel id: {self.pxm_RelationshipDict.get(text)}")   
    
    def cmp_typeChanged(self, text):
        self.cmp_relationship_id_lineedit.setText(f"cmp_rel id: {self.cmp_RelationshipDict.get(text)}")   

    def add_relationship(self):
        # 提取QLineEdit的内容
        instance1_id = self.selected_points_id_lineedit1.text()
        instance2_id = self.selected_points_id_lineedit2.text()
        instance1_label = self.selected_points_label_lineedit1.text()
        instance2_label = self.selected_points_label_lineedit2.text()
        sup_relationship_id = self.sup_relationship_id_lineedit.text()
        sup_relationship_text = self.sup_cb.currentText()
        pxm_relationship_id = self.pxm_relationship_id_lineedit.text()
        pxm_relationship_text = self.pxm_cb.currentText()
        cmp_relationship_id = self.cmp_relationship_id_lineedit.text()
        cmp_relationship_text = self.cmp_cb.currentText()

        sceneId = self.json_data["sceneId"]
        
        if  sup_relationship_text == 'None':
            sup_relationship_tuple = None
        else:    
            sup_relationship_tuple = [int(instance1_id.strip().split(': ')[1]), int(instance2_id.strip().split(': ')[1]), int(sup_relationship_id.strip().split(': ')[1]), sup_relationship_text]
        if  pxm_relationship_text == 'None':
            pxm_relationship_tuple = None
        else: 
            pxm_relationship_tuple = [int(instance1_id.strip().split(': ')[1]), int(instance2_id.strip().split(': ')[1]), int(pxm_relationship_id.strip().split(': ')[1]), pxm_relationship_text]
        if  cmp_relationship_text == 'None':
            cmp_relationship_tuple = None
        else: 
            cmp_relationship_tuple = [int(instance1_id.strip().split(': ')[1]), int(instance2_id.strip().split(': ')[1]), int(cmp_relationship_id.strip().split(': ')[1]), cmp_relationship_text]
        
        if instance1_label != 'SPLIT' and instance2_label != 'SPLIT':
            self.add_rel(sup_relationship_tuple, pxm_relationship_tuple, cmp_relationship_tuple)

    def add_rel(self, sup_rel, pxm_rel, cmp_rel):
        if sup_rel is not None:    
            self.all_rels['sup_Rel'].append(sup_rel)
        if pxm_rel is not None:
            self.all_rels['pxm_Rel'].append(pxm_rel)
        if cmp_rel is not None:
            self.all_rels['cmp_Rel'].append(cmp_rel)
        logging.info(f"stack:{sup_rel}, {pxm_rel}, and {cmp_rel}")
    
    def write_to_json(self, all_rels):
        if len(self.all_rels['sup_Rel']) == 0 and len(self.all_rels['pxm_Rel']) == 0 and len(self.all_rels['cmp_Rel']) == 0:
            logging.debug(f"Empty")
        else:
            logging.info(f"start write Relations")
            #file_path = "/home/mint/annotate/anno.json"
            file_path = "/home/shenjunhao/Annotate_3DSG/anno.json"
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError):
                data = []
            
            for rels in data:
                if rels['SceneId'] == self.all_rels['SceneId']:
                    data.remove(rels)
                    break
                
            data.append(all_rels)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=4)
            logging.debug(f"write Relation: {all_rels}")
    
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