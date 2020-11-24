import math
import numpy as np
import csv
import json
import pandas as pd
from System import System
from Satellite import Satellite

def csv_read(file_path):
    df = pd.read_csv(file_path)
    return df.fillna(0) #NaNを0埋め
    
def json_read(file_path):
    json_open = open(file_path,'r')
    json_dict = json.load(json_open)
    return json_dict

compo_df = csv_read('csv/Components.csv')
link_df = csv_read('csv/Link.csv')
COM_df = csv_read('csv/Command.csv')
TEL_df = csv_read('csv/Telemetry.csv')
COM_path_dict = json_read('json/Command_path.json')
Compo_state_dict = json_read('json/Component_state.json')
COM_type_dict = json_read('json/Command_type.json')

def main():
    targetCOM = [27]
    targetTEL = [17]    
    ini_COM = [27]
    #ini_TELも考える必要がありそう

    sat = Satellite(compo_df, link_df, COM_df, TEL_df, COM_type_dict)
    sat.init_state(ini_COM, Compo_state_dict)
    #実験
    #sat.COM[2].init(COM_path_dict['2'])
    sat.find_target_path(targetTEL, targetCOM)
    #print(sat.targetCOMpath)
    sys = System(sat)
    sys.verify_plan()
    #完了してたら原因不明
    print("faulty COMlink:", sys.sat.targetCOMpath, "faulty TELlink:",sys.sat.targetTELpath) #最終的な残り
    
if __name__ == "__main__":
    main()
