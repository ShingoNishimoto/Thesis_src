import copy
from collections import OrderedDict
import numpy as np
from Process import Process

class System():
    def __init__(self, sat):
        self.sat = sat
        self.candidates = {}
        self.total_candidates = {COM_ID : {"COM":[], "TEL":[]} for COM_ID in self.sat.COM.keys()}
        self.effectness = {COM_ID : {} for COM_ID in self.sat.COM.keys()}
        self.negative_effect = {COM_ID : {} for COM_ID in self.sat.COM.keys()}
        #初期値どうするべきか
        self.human_select = 0
        self.selectedCOM = []
        self.remainingCOM = [ID for ID in self.sat.COM.keys()]
        self.all_process = {} #ID:Process
        self.results = [] #終端までのコマンド数と確率をためる
    
    def init_element(self, df):
        self.elements = []
        #とりあえずlistに収める形だけ実装．細かい体裁は下位で実装
        for row in df.itertuples():
            self.elements.append(row)

    def verify_plan(self):
    #まずはテレメトリのみでの確認ができるか判定．つまりコマンドによる変化なしで状態変化する状態量の確認
    #この時にtargetTELで与えられたものは除く
    #テレメトリに関して，下ろしているものなのかそうでないのかを考えていない
        #candidate_TEL_ID = []
        for TEL_ID in self.sat.TEL.keys():
            if (not self.sat.targetCOMpath and not self.sat.targetTELpath):
                return 0
            elif TEL_ID in self.sat.targetTEL_ID:
                continue
            elif self.sat.TEL[TEL_ID].trigger == 'Time' and self.sat.TEL[TEL_ID].availability:
                #TELによる検証
                self.verify_by_TEL(TEL_ID)
                
            #コマンドがトリガーのものでもinitial_COMにあるものなら見れるが，後に見る
            elif self.sat.TEL[TEL_ID].trigger == 'Command':
                continue
        print("\n Check telemetries which influenced by initial Command state\n")
        #空判定
        if self.sat.initial_COM:
            for iniCOM_ID in self.sat.initial_COM:
                #この時の更新はiniCOMなので入力関係ない．結果の確認だけ必要
                #この前になにを確認するのかという表示が必要
                self.verify_by_COM(iniCOM_ID)
                #このコマンドが検証できるポート数を数える．
            
        #コマンドによる検証に入る．
        while(1):
            if(self.verify_by_COM()):
                print("finish")
                break
            print("selected Command:",self.selectedCOM,"remaining Command:",self.remainingCOM)
    
    def find_total_link(self, COM_ID, Process=0):
        if not Process:
            top = self
        else:
            top = Process
        total_candidates = top.total_candidates
        candidates = top.candidates
        effectness = top.effectness
        #初期化
        total_candidates[COM_ID]["COM"] = []
        total_candidates[COM_ID]["TEL"] = []
        for key in candidates.keys():
            #telに関するものは飛ばす
            if (len(key)<2):
                continue
            elif key[0]!=COM_ID:
                continue
            else:
                total_candidates[COM_ID]["COM"] = list(set(total_candidates[COM_ID]["COM"] + \
                candidates[key]["COM"]))
                total_candidates[COM_ID]["TEL"] = list(set(total_candidates[COM_ID]["TEL"] + \
                candidates[key]["TEL"]))
                effectness[COM_ID]["candidate link number"] = len(total_candidates[COM_ID]["COM"]) + \
                len(total_candidates[COM_ID]["TEL"])
                #print(self.candidates[key]["veri_link_num"])
                
    def verify_by_TEL(self, TEL_ID):
        self.candidates.update(self.sat.search_TEL(TEL_ID))
        #verifyできるものがない場合ははじく
        if not self.candidates[(TEL_ID,)]["TEL"]:
            return 0
        print("TELtarget:",self.sat.targetTELpath)
        print("Telemetry",TEL_ID,"(",self.sat.TEL[TEL_ID].name, ") can verify following links\n", self.candidates[(TEL_ID,)]["TEL"])
        #まずここで確認してもらうか
        self.human_select = TEL_ID
        self.receive_results(TEL_ID)
        self.update_target_path("TEL")
        
    #オーバーロードする
    def verify_by_COM(self, COM_ID=0):
        if not self.remainingCOM:
            return 1
        #processごとに持つ確認済みコマンド
        process_checkedCOM = copy.deepcopy(self.selectedCOM)
        #現状の提示
        print("COMtarget:",self.sat.targetCOMpath,"TELtarget:",self.sat.targetTELpath)
        if not COM_ID:
            #初期化．これはもう使ってない指標な気がする．そのリンクを通るコマンドの数
            for COM_l in self.sat.COMlinks.values():
                COM_l.verifyCOMnum = 0
            for TEL_l in self.sat.TELlinks.values():
                TEL_l.verifyCOMnum = 0
            #探索開始
            for COM_ID in self.remainingCOM:
                ProcessID = {"Parent":0,"result":0} #最初なので0を入れている
                if COM_ID in (self.sat.targetCOM_ID or self.selectedCOM): 
                    continue
                #残りがなくなるか，対象がなくなれば終了
                elif (not self.sat.targetCOMpath and not self.sat.targetTELpath):
                    print("nothing target")
                    return 1
                else:
                    #0が返ってきたら飛ばす
                    if self.search_candidate_calculate(COM_ID)==0:
                        continue
                    #ここで次のコマンドを探すループを付けなければいけない
                    #探索を行うのはすべての検証が終わるまで．
                    process = Process(self.sat,COM_ID,self.candidates,ProcessID)
                    #print(process.ID)
                    self.all_process[process.ID] = process
                    
                    process.Process_flow()
                    #ここでresultを受け取って，各結果ごとに再探索を行う．
                    self.update_by_TEL_result(process,COM_ID,process_checkedCOM)
                    
                    self.calculate_total_score(COM_ID)
                    #ここでポイント表示したい
                    self.show_point(COM_ID)
                    #残りはあるけど，検証に使えないときは？
                    #print(COM_ID,":backup num", self.sat.COM[COM_ID].candidateTELnum)
                #print(self.all_process)
            flag = 0
            for remainCOM in self.remainingCOM:
                #flagが立ってたら，次に行ける
                if self.sat.COM[remainCOM].verify_flag:
                    flag = 1
                    break
                else:
                    continue
            #全部通過したら終了
            if not flag:
                print("nothing can verify")
                return 1
            
            #ここが実際の検証を行うところ
            self.receive_selection()
            #故障箇所を見つけたら即終了する形になっていない．Processのresultを使用するべき
        #iniCOM用
        else:
            if COM_ID in self.selectedCOM:
                return 1
            #残りがなくなるか，対象がなくなれば終了
            elif (not self.sat.targetCOMpath and not self.sat.targetTELpath):
                return 1
            else:
                self.search_candidate_calculate(COM_ID)
            
            self.receive_selection(COM_ID)
        self.update_target_path("COM")
    
    # 候補見つけて，ポイントとか計算する流れを別関数化したい.
    # 最終まで見つけるループを回して，
    # その結果をメモ化しておくことで人の選択に応じて提示するだけにできる．
    # ここに必要な機能は，候補見つける．計算する．
    def search_candidate_calculate(self, COM_ID, Process=0):
        if not Process:
            top = self
        else:
            top = Process
        top.candidates.update(top.sat.find_check_COM(COM_ID))
        self.find_total_link(COM_ID,Process)
        #self.count_COM_num_for_link(COM_ID)
        #候補がないものは飛ばす
        if not top.total_candidates[COM_ID]["COM"] and not top.total_candidates[COM_ID]["TEL"]:
            return 0
        #ここに確認可能性リンクの平均計算
        self.calculate_mean_check_link_number(COM_ID,Process)
        #print(self.candidates)
        ##self.count_COM_num_for_link(COM_ID)
        self.propagate_COM_effect(COM_ID,Process)
        #電力がマイナスになるものは禁止
        if not self.calculate_point(COM_ID,Process):
            print("NG")
            return 0
            #選択肢として表示しないような処理必要

    #名前おかしい
    # 残るリンクを渡していけばいい(copy of targetCOM(TEL)path)
    # result_dictは最終的な集計
    def update_by_TEL_result(self,process,COM_ID,checkedCOM):
        #process.each_resultもらってそれぞれに関しれ次の探索に行きたい
        #残りの故障候補を更新してこれをProcess.sat.targetpathに渡すようにする？
        next_checkedCOM = checkedCOM + [COM_ID]
        remainingCOM = list(set([i for i in self.sat.COM.keys()]) - set(next_checkedCOM))
        
        for key, result in process.each_result.items():
            #print(key,result)
            #このリセットが必要？
            ID = {"Parent":process.ID}
            #ほしい情報はnormal link or abnormal link
            #テレメトリの結果ごとに新たなProcess生成←これは違う．
            # 結果から出てくるコマンドの候補ごとに生成するのが正解．
            #targetの更新だけして，それをnextに渡せるようにすればいい
            next_sat = copy.deepcopy(process.sat)
            next_sat.targetCOMpath = list(set(next_sat.targetCOMpath) \
                - set(result["normal_link"]["COM"]))
            next_sat.targetTELpath = list(set(next_sat.targetTELpath) \
                - set(result["normal_link"]["TEL"]))
            #abnormalが見つかったものや，既に終えたものはsys側で保持しておく
            if result["abnormal_link"]["COM"] or result["abnormal_link"]["TEL"] or\
                 (not next_sat.targetCOMpath and not next_sat.targetTELpath):
                #resultが次のプロセスを持つことにする．終了したときは何もないけど，フラグ立てとく
                #print(key,result["abnormal_link"]["COM"])
                #フラグ立てる条件がここだけやと死ぬ説->死んだ
                result["Fin"] = True
                continue
            #ここら辺で未処理のテレメトリがあるやつは次に行かんようにするとか？
            # それかそもそも途中の結果を入れないとか
            else:
                #終わって無くても全てのテレメトリを見ていない場合には次にいかない
                if len(key) < len(process.sat.COM[COM_ID].candidate_TEL_ID):
                    continue
                #find next com
                ID["result"] = key
                #print(key)
                #print(ID)
                #resultのnext_process更新したほうがいいかも
                self.generate_next_process(remainingCOM,copy.deepcopy(process),next_sat,ID,result)
                
            #self.
            
           
    #processのコピーを渡す
    def generate_next_process(self,remainingCOM,current_process,next_sat,ID,result):
        current_process.sat = next_sat
        checkedCOM = list(set([i for i in self.sat.COM.keys()]) - set(remainingCOM))
        flag = 0
        for nextCOM_ID in remainingCOM:
            if nextCOM_ID in self.sat.targetCOM_ID: 
                continue
            else:
                #0が返ってきたら飛ばす
                if self.search_candidate_calculate(nextCOM_ID,current_process)==0:
                    continue
                #見つけたらフラグ立てる
                flag = 1
                #print(nextCOM_ID)
                next_process = Process(current_process.sat,nextCOM_ID,current_process.candidates,copy.deepcopy(ID))
                result["next_processes"].append(next_process.ID)
                #ここでの追加の時点でおかしいんやろな
                self.all_process[next_process.ID] = next_process
                next_process.Process_flow()
                self.update_by_TEL_result(next_process,nextCOM_ID,checkedCOM)
        #全て通過したプロセスは次がなかったということ．->終了と同義
        if flag==0:
            result["Fin"] = True

    

    #テレメトリ結果が正常なのかどうかという確率を計算する
    #def 
    
    def count_COM_num_for_link(self,COM_ID):
        #COM
        for COMp in self.sat.COMlinks.values():
            if COMp.ID in self.total_candidates[COM_ID]["COM"]:
                COMp.verifyCOMnum = COMp.verifyCOMnum + 1
        #TEL
        for TELp in self.sat.TELlinks.values():
            if TELp.ID in self.total_candidates[COM_ID]["TEL"]:
                TELp.verifyCOMnum = TELp.verifyCOMnum + 1
            
    def calculate_point(self,COM_ID,Process=0):
        if not Process:
            top = self
        else:
            top = Process
        #レア度を計算．要らんぽい
        '''
        allCOMnum = len(self.sat.COM)
        self.effectness[COM_ID]["COMrareness"] = 0
        for COMl_ID in self.total_candidates[COM_ID]["COM"]:
            P_COM_num = float(self.sat.COMlinks[COMl_ID].verifyCOMnum)/allCOMnum
            self.effectness[COM_ID]["COMrareness"] = self.effectness[COM_ID]["COMrareness"] + \
            -P_COM_num*math.log(P_COM_num,allCOMnum)
            
        #allTELnum = len(self.sat.TEL)
        for TELl_ID in self.total_candidates[COM_ID]["TEL"]:
            P_COM_num = float(self.sat.TELlinks[TELl_ID].verifyCOMnum)/allCOMnum
            #self.effectness[COM_ID]["COMrareness"] = self.effectness[COM_ID]["COMrareness"] + \
            #-P_COM_num*math.log(P_COM_num,allCOMnum)
        '''
        #引き出しの多さ
        #self.effectness[COM_ID]["back_up_TELnum"] = self.sat.COM[COM_ID].candidateTELnum
        #以下でネガティブポイントを計算
        top.negative_effect[COM_ID]["impact TEL num"] = len(top.sat.COM[COM_ID].impact_TEL_ID)
        
        if top.sat.RemainingPower < 0:
            return 0
        #ここは現在の状態に応じて計算を変えないといけない．というか，状態を変化させないコマンドを飛ばすようにすればいい．
        top.negative_effect[COM_ID]["Remaining Power"] = round(top.sat.RemainingPower + top.sat.COM_consume_power,3)
        top.negative_effect[COM_ID]["Power consume by this COM"] = round(top.sat.COM_consume_power,3)
        #姿勢変化の影響を追加
        top.negative_effect[COM_ID]["Attitude"] = "Keep" #default
        target = top.sat.COM[COM_ID].target[0]
        target_compo_name, target_fnc_name_list = target["Component"], target["Function"]
        #Functionあるやつだけ
        if target_fnc_name_list:
            Compo = top.sat.compos[target_compo_name]
            target_fnc = Compo.Function[target_fnc_name_list[0]]
            if "Attitude" in target_fnc:
                if target_fnc["Attitude"]=="change":
                    top.negative_effect[COM_ID]["Attitude"] = "Change"
        return 1
    
    def calculate_total_score(self,COM_ID):
        #最終までのコマンド数
        all_COM_num = 1
        P_result = 1
        self.results = []
        #topを探す
        for ID,process in self.all_process.items():
            #topはparentが0である 
            if COM_ID==ID[2][1] and ID[0][1]==0:
                top_process = process
                self.top_ID = ID
                #print(COM_ID)
                #print(ID,process.each_result)
                break
        
        #topを持つ子を探す．を繰り返す．
        self.recurrent_child_search(top_process,all_COM_num,P_result)
        #結果の平均を取る．
        #print(self.results)
        self.effectness[COM_ID]["total_COM_number"] = sum([d["P"]*d["COM_num"] for d in self.results])

    #parentをもとにして子を探す再帰関数
    def recurrent_child_search(self,parent,all_COM_num,P_result):
        #key_buff = []
        for key, result in parent.each_result.items():
            if result["next_processes"]:
                P_next = P_result*result["P"]
                next_COM_num = all_COM_num + 1
                for next_ID in result["next_processes"]:
                    if next_ID in self.all_process.keys():
                    #このプロセスを親に持つ子を探す
                        self.recurrent_child_search(self.all_process[next_ID],next_COM_num,P_next)
                    #ない場合はやめる
                    else:
                        continue
            #次がないものかつ，終了しているものを見たい
            elif result["Fin"]:
                #複数回同じものが確率が累積されてはいっている．
                # というより，不完全な状態（途中結果のもの）で次のコマンドに行ってるものがある
                self.results.append({"P":P_result*result["P"],"COM_num":all_COM_num,"result":result["history"]})
        '''
        for ID,process in self.all_process.items():
            if ID[0][1]==parent.ID:
                #確率を計算
                P_next = P_result*parent.each_result[ID[1][1]]["P"]
                next_COM_num = all_COM_num + 1
                key_buff.append(ID[1][1])
                #このプロセスを親に持つ子を探す
                self.recurrent_child_search(process,next_COM_num,P_next)
                #このプロセスで次に行かない結果のものはここで確率をまとめたい
            else:
                continue
        #子プロセスを持っていない結果のkeyを取得したい
        if key_buff:
            #print(key_buff)
            for key,each in parent.each_result.items():
                if key in key_buff:
                    continue
                self.results.append({"P":P_result*each["P"],"COM_num":all_COM_num,"result":key})
        else:
        #全部通過したら子がない．ここに途中結果のものも追加されてしまっている．．．．
            #next_processがないものだけ考える
            print("through process:",parent.each_result)
            for ID,result in parent.each_result.items():
                if result["next_processes"]:
                    continue
                #self.results.append({"P":P_result,"COM_num":all_COM_num,"result":None})
        '''
    #確率計算
    def calculate_probability(self,pair,route_dict,COM_route,TEL_route,candidate_buff_list,link_num,P_dict,TELorCOM,Process=0):
        if not Process:
            top = self
        else:
            top = Process
        flag = TELorCOM
        if TELorCOM=="COM":
            #other_flag = "TEL"
            Link1 = top.sat.COMlinks
            Link2 = top.sat.TELlinks
            route = COM_route
            other_route = TEL_route
        else:
            #other_flag = "COM"
            Link1 = top.sat.TELlinks
            Link2 = top.sat.COMlinks
            route = TEL_route
            other_route = COM_route

        for link in copy.deepcopy(route_dict[flag]):
            P_li_R = 1
            #ループで考えるので，COM(TEL)も考える必要がある
            for other_link in route[pair]:
                if link != other_link:
                    P_li_R = P_li_R*Link1[other_link].probability
            for other_link in other_route[pair]: 
                P_li_R = P_li_R*Link2[other_link].probability
            link_num = link_num + P_li_R
            P_dict[link] = P_li_R
            #次の経路での確認可能性の計算に入らないようにremove 
            for i in range(len(candidate_buff_list)):
                next_route = candidate_buff_list[i]
                if link in next_route[1][flag]:
                    candidate_buff_list[i][1][flag].remove(link)
            #print(link, P_li_R, link_num)
        top.candidates[pair]["P_route"][flag] = P_dict
        return link_num
    
    #コマンドと影響を受ける各テレメトリの経路でLinkを確認できる確率と
    # リンク数の期待値を考える
    def calculate_mean_check_link_number(self, COM_ID, Process=0):
        if not Process:
            top = self
        else:
            top = Process
        candidate_buff = {}
        #確認候補がある組み合わせから探す
        for TEL_ID in top.sat.COM[COM_ID].candidate_TEL_ID:
            #コピる
            candidate_buff[(COM_ID,TEL_ID)] = top.candidates[(COM_ID,TEL_ID)]
        #print(self.sat.COM[COM_ID].candidate_TEL_ID)
        #経路が短い順にソートしたものをコピー
        candidate_buff_list = copy.deepcopy(sorted(candidate_buff.items(), key=lambda x:len(x[1]["COM"]+x[1]["TEL"])))
        #print(candidate_buff_list)
        top.effectness[COM_ID]["Check link number"] = 0
        
        COM_route = {}
        TEL_route = {}
        #最初にコピる
        for route_dict in candidate_buff_list:
            COM_route[route_dict[0]] = copy.deepcopy(route_dict[1]["COM"])
            TEL_route[route_dict[0]] = copy.deepcopy(route_dict[1]["TEL"])
     
        #ここのアルゴリズムも修正した方がいい．確率最大な部分をとるように
        # 短い順が必ずしも確率の低い場合とは限らない．それぞれのリンクの確率が一様でないときもある．
        # リンクの確率が一様でないときは経路ごとに確率の大きさを考えても何の意味もない
        # candidateの中に確認可能性も持たせる．確率は各リンクごとに
        #確率計算の部分だけ別関数化したいな
        for pair,route_dict in candidate_buff_list:
            link_num = 0
            top.candidates[pair]["P_route"] = {}
            #print(loop[route_dict[0]])
            P_dict = {}
            #COM
            link_num = self.calculate_probability(pair,route_dict,COM_route,TEL_route,candidate_buff_list,link_num,P_dict,"COM",Process)
       
            #TEL用に初期化
            P_dict = {}
            link_num = self.calculate_probability(pair,route_dict,COM_route,TEL_route,candidate_buff_list,link_num,P_dict,"TEL",Process)
            
            #この経路における平均を計算
            #空の場合の処理も必要
            P_COM_dict = top.candidates[pair]["P_route"]["COM"]
            P_TEL_dict = top.candidates[pair]["P_route"]["TEL"]

            if not P_COM_dict and not P_TEL_dict:
                average = 0
            else:
                if not P_COM_dict:
                    P_list = list(P_TEL_dict.values())
                elif not P_TEL_dict:
                    P_list = list(P_COM_dict.values())
                else:
                    P_list = list(P_COM_dict.values()) + list(P_TEL_dict.values())
                if len(P_list)==1:
                    average = P_list[0]
                else:    
                    average = np.average(P_list)
            top.candidates[pair]["P_route"]["average"] = average
        
                #print(TELlink, P_li_R,link_num)
            #コマンドによる数を合計
            top.effectness[COM_ID]["Check link number"] = top.effectness[COM_ID]["Check link number"] + link_num
            top.effectness[COM_ID]["Mean Probability of check"] = top.effectness[COM_ID]["Check link number"]/top.effectness[COM_ID]["candidate link number"]
    
    #あと表示結果は経路が短い順にした方が良いと思う
    def show_candidates(self):
        for key in self.candidates.keys():
            #telに関するものは飛ばす
            if (len(key)<2):
                continue
            #これは何？→関係ないコマンドに関して省いている
            elif key[0]!=self.human_select:
                #print(key)
                continue
            elif not self.candidates[key]["COM"] and not self.candidates[key]["TEL"]:
                #print(key)
                continue
            print("Command",key[0],"(",self.sat.COM[key[0]].name, ") & Telemetry",\
                  key[1],"(", self.sat.TEL[key[1]].name, ") can verify following links\n",\
              "COMlink:",self.candidates[key]["COM"], "TELlink", self.candidates[key]["TEL"])
        #print("check those corresponding Telemetry")

    #デフォルト値使ってオーバーロードする
    def receive_selection(self, COM_ID=0):
        if not COM_ID:
            while(1):
                self.human_select = input("Please select Command above(input ID) >>")
                #入力が数字
                if str.isdecimal(self.human_select):
                    if int(self.human_select) in self.remainingCOM:
                        self.human_select = int(self.human_select)
                        self.show_candidates()
                        break
                else:
                    continue                    
        else:
            self.human_select = COM_ID
            self.show_candidates()
        self.selectedCOM.append(self.human_select)
        self.remainingCOM = list(set(self.remainingCOM) - set(self.selectedCOM))
    
    def receive_results(self,TEL_ID):
        while(1):
            #初めに入力を受け付ける
            print("\nPlease check", self.sat.TEL[TEL_ID].name)
            self.result = input("Input result(OK or NG)>>")
            if (self.result!="OK" and self.result!="NG"):
                self.result = input("Please input OK or NG >>")
                if (self.result!="OK" and self.result!="NG"):
                    continue
                else:
                    break
            else:
                break
        #チェックしたものを再度確認しないようにフラグ必要←これいる？
        #self.sat.TEL[TEL_ID].checked_flag = 1
   
   #ここでProcessの結果を利用するべき．
   # どのプロセスを利用したのかは打ったコマンドと，その前の状態からわかる．
   # そのプロセスの結果と人間が入力した結果を照らし合わせて次の行動を決めるべき．
   # abnormalが見つかった場合にはtargetから除いて新たにabnormal linkをSystemで
   # 持つようにするのがいいかもしれない．次に行くかどうかをそれをもとに判断させるようにする．
    def update_target_path(self, TELorCOM):
        if(TELorCOM=="COM"):
            COM_ID = self.human_select
            #ここで確認した組み合わせは不要だからcandidatesから消す？
            for TEL_ID in self.sat.COM[COM_ID].impact_TEL_ID:
                select_key = (COM_ID,TEL_ID)
                if not self.sat.targetCOMpath:
                    break
                #不具合検知の組み合わせ 
                if TEL_ID in self.sat.targetTEL_ID and COM_ID in self.sat.targetCOM_ID:
                    continue
                #verify link なし
                elif (not self.candidates[select_key]["COM"] and not self.candidates[select_key]["TEL"]):
                    continue
                #確認してもらう
                else:
                    self.receive_results(TEL_ID)
                if(self.result=="NG"):
                    continue
                else:
                    #print(self.candidates[select_key])
                    for COMlinkID in self.candidates[select_key][TELorCOM]:
                        self.sat.COMlinks[COMlinkID].valid = 1
                        #print("veified COMlinkID:",COMlinkID)
                    for TELlinkID in self.candidates[select_key]["TEL"]:
                        self.sat.TELlinks[TELlinkID].valid = 1
                        #print("verified TELlinkID:",TELlinkID)
                print("COMlink:",self.candidates[select_key][TELorCOM], "& TELlink:",\
                      self.candidates[select_key]["TEL"], "were verified")
                #targetの更新
                self.sat.targetCOMpath = self.sat.check_links(self.sat.targetCOMpath, self.sat.COMlinks)
                self.sat.targetTELpath = self.sat.check_links(self.sat.targetTELpath, self.sat.TELlinks)
                self.sat.update_link_probability()
                
                self.search_candidate_calculate(COM_ID)
                #print(self.candidates[select_key])
                #ここでポイント表示したい
                self.show_point(COM_ID)
            #確認フラグを戻す
            for TEL_ID in self.sat.COM[COM_ID].impact_TEL_ID:
                self.sat.TEL[TEL_ID].checked_flag = 0
            return 1
        #TEL
        else:
            select_key = (self.human_select,)
            if(self.result=="NG"):
                return 0
            else:
                #各ポートのvalidを更新
                for p_ID in self.candidates[select_key][TELorCOM]:
                    self.sat.TELlinks[p_ID].valid = 1
                    #print("verified TELlinkID:",p_ID)
                print("TELlink:", self.candidates[select_key]["TEL"], "were verified")
                self.sat.targetTELpath = self.sat.check_links(self.sat.targetTELpath, self.sat.TELlinks)
                self.sat.update_link_probability()
                return 1
            
    #これを使って表示する前に効果と波及効果の大きさをもとにソートして，一部だけの表示にする．
    def show_point(self, COM_ID):
        #既に打ったものは表示しない
        if COM_ID in self.selectedCOM:
            return 0
        elif not self.total_candidates[COM_ID]["COM"] and not self.total_candidates[COM_ID]["TEL"]:
            return 0
        #効果を表示
        print("COM", COM_ID, self.sat.COM[COM_ID].name,"\n\t", self.effectness[COM_ID],\
            "\n\t",self.negative_effect[COM_ID])
        
    #そのコマンドを打つとどうなるかを更新する
    #これはあくまでも可能性の更新．本当にそのような遷移をしたかは，テレメトリの結果に依存する．←これはどうやって実装する？
    #状態変化するものだけに適用していればiniCOMに対して行っても問題ない
    def propagate_COM_effect(self,COM_ID,Process=0):
        if not Process:
            top = self
        else:
            top = Process
        previous_compo_state = {}
        #ACTION
        if top.sat.COM[COM_ID].type == "ACTION":
            for target in top.sat.COM[COM_ID].target:
                compo = top.sat.compos[target["Component"]]
                previous_compo_state[compo.name] = copy.deepcopy(compo.Active)
                #電源操作系のコマンドはFunctionが空
                if not target["Function"]:
                    if top.sat.COM[COM_ID].Active and not compo.Active:
                        compo.Active = True
                        top.sat.COM_consume_power = compo.PowerConsumption
                    elif not top.sat.COM[COM_ID].Active and compo.Active:
                        compo.Active = False
                        top.sat.COM_consume_power = - compo.PowerConsumption
                    else:
                        top.sat.COM_consume_power = 0
                #コマンドがFunctionを持つ場合
                else:
                    for func in target["Function"]:
                        #コンポーネントはFunctionの名前をキーとして持つ
                        if top.sat.COM[COM_ID].Active and not compo.Function[func]["Active"]:
                            compo.Function[func]["Active"] = True
                            top.sat.COM_consume_power = compo.Function[func]["PowerConsumption"]
                        elif not top.sat.COM[COM_ID].Active and compo.Function[func]["Active"]:
                            compo.Function[func]["Active"] = False
                            top.sat.COM_consume_power = - compo.Function[func]["PowerConsumption"]
                        else:
                            top.sat.COM_consume_power = 0
            top.sat.update_Power_state()
            #もどす
            for name in previous_compo_state.keys():
                top.sat.compos[name].Active = previous_compo_state[name]
        #今は未実装なだけ，GETとかを実装する
        #GET
        elif top.sat.COM[COM_ID].type == "GET":
            
            return 0
    