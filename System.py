import copy
from collections import OrderedDict
import numpy as np

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
    
    def find_total_link(self, COM_ID):
        #初期化
        self.total_candidates[COM_ID]["COM"] = []
        self.total_candidates[COM_ID]["TEL"] = []
        for key in self.candidates.keys():
            #telに関するものは飛ばす
            if (len(key)<2):
                continue
            elif key[0]!=COM_ID:
                continue
            else:
                self.total_candidates[COM_ID]["COM"] = list(set(self.total_candidates[COM_ID]["COM"] + \
                self.candidates[key]["COM"]))
                self.total_candidates[COM_ID]["TEL"] = list(set(self.total_candidates[COM_ID]["TEL"] + \
                self.candidates[key]["TEL"]))
                self.effectness[COM_ID]["candidate link number"] = len(self.total_candidates[COM_ID]["COM"]) + \
                len(self.total_candidates[COM_ID]["TEL"])
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
                if COM_ID in (self.sat.targetCOM_ID or self.selectedCOM): 
                    continue
                #残りがなくなるか，対象がなくなれば終了
                elif (not self.sat.targetCOMpath and not self.sat.targetTELpath):
                    print("nothing target")
                    return 1
                else:
                    self.candidates.update(self.sat.find_check_COM(COM_ID))
                    self.find_total_link(COM_ID)
                    #ここに確認可能性リンクの平均計算
                    self.calculate_mean_check_link_number(COM_ID)
                    #print(self.candidates)
                    #現状でのコマンドによって検証できる箇所の洗い出しが終了したので，
                    #あるポートを検証できるコマンドの数を調べる．
                    self.count_COM_num_for_link(COM_ID)
                    self.propagate_COM_effect(COM_ID)
                    #電力がマイナスになるものは禁止
                    if not self.calculate_point(COM_ID):
                        print("NG")
                        continue
                        #選択肢として表示しないような処理必要
                    #ここで次のコマンドを探すループを付けなければいけない
                    #探索を行うのはすべての検証が終わるまで．

                    #ここでポイント表示したい
                    self.show_point(COM_ID)
                    #残りはあるけど，検証に使えないときは？
                    #print(COM_ID,":backup num", self.sat.COM[COM_ID].candidateTELnum)
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
        #iniCOM用
        else:
            if COM_ID in self.selectedCOM:
                return 1
            #残りがなくなるか，対象がなくなれば終了
            elif (not self.sat.targetCOMpath and not self.sat.targetTELpath):
                return 1
            else:
                self.candidates.update(self.sat.find_check_COM(COM_ID))
                self.find_total_link(COM_ID)
                self.count_COM_num_for_link(COM_ID)
            self.receive_selection(COM_ID)
        self.update_target_path("COM")

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
            
    def calculate_point(self,COM_ID):
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
        self.negative_effect[COM_ID]["impact TEL num"] = len(self.sat.COM[COM_ID].impact_TEL_ID)
        
        if self.sat.RemainingPower < 0:
            return 0
        #ここは現在の状態に応じて計算を変えないといけない．というか，状態を変化させないコマンドを飛ばすようにすればいい．
        self.negative_effect[COM_ID]["Remaining Power"] = round(self.sat.RemainingPower + self.sat.COM_consume_power,3)
        self.negative_effect[COM_ID]["Power consume by this COM"] = round(self.sat.COM_consume_power,3)
        return 1
    
    #コマンドと影響を受ける各テレメトリの経路でLinkを確認できる確率と
    # リンク数の期待値を考える
    def calculate_mean_check_link_number(self, COM_ID):
        candidate_buff = {}
        #確認候補がある組み合わせから探す
        for TEL_ID in self.sat.COM[COM_ID].candidate_TEL_ID:
            #コピる
            candidate_buff[(COM_ID,TEL_ID)] = self.candidates[(COM_ID,TEL_ID)]
        #print(self.sat.COM[COM_ID].candidate_TEL_ID)
        #経路が短い順にソートしたものをコピー
        candidate_buff_list = copy.deepcopy(sorted(candidate_buff.items(), key=lambda x:len(x[1]["COM"]+x[1]["TEL"])))
        #print(candidate_buff_list)
        self.effectness[COM_ID]["Check link number"] = 0
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
        for route_dict in candidate_buff_list:
            link_num = 0
            self.candidates[route_dict[0]]["P_route"] = {}
            #print(loop[route_dict[0]])
            P_dict = {}
            for COMlink in copy.deepcopy(route_dict[1]["COM"]):
                P_li_R = 1
                #ループで考えるので，TELlinkも考える必要がある
                for other_link in COM_route[route_dict[0]]:
                    if COMlink != other_link:
                        P_li_R = P_li_R*self.sat.COMlinks[other_link].probability
                for other_link in TEL_route[route_dict[0]]: 
                    P_li_R = P_li_R*self.sat.TELlinks[other_link].probability
                link_num = link_num + P_li_R
                P_dict[COMlink] = P_li_R
                #次の経路での計算に入らないようにremove
                for i in range(len(candidate_buff_list)):
                    other_route = candidate_buff_list[i]
                    if COMlink in other_route[1]["COM"]:
                        #print(COMlink)
                        candidate_buff_list[i][1]["COM"].remove(COMlink)
                #print(COMlink, P_li_R, link_num)
            #COMlinkの分を回収．
            self.candidates[route_dict[0]]["P_route"]["COM"] = P_dict
            self.candidates[route_dict[0]]["P_route"]["average"] = np.average(list(P_dict.values()))
            #TEL用に初期化
            P_dict = {}
            for TELlink in copy.deepcopy(route_dict[1]["TEL"]):
                P_li_R = 1
                for other_link in TEL_route[route_dict[0]]:
                    if TELlink != other_link:
                        P_li_R = P_li_R*self.sat.TELlinks[other_link].probability
                for other_link in COM_route[route_dict[0]]:
                    P_li_R = P_li_R*self.sat.COMlinks[other_link].probability
                link_num = link_num + P_li_R
                P_dict[TELlink] = P_li_R
            #次の経路での計算に入らないようにremove
                for i in range(len(candidate_buff_list)):
                    other_route = candidate_buff_list[i]
                    if TELlink in other_route[1]["TEL"]:
                        #print(TELlink)
                        candidate_buff_list[i][1]["TEL"].remove(TELlink)
            #この経路で見た時の確認可能性TELlinkの分を回収．
            self.candidates[route_dict[0]]["P_route"]["TEL"] = P_dict 
            #この経路における平均を計算
            self.candidates[route_dict[0]]["P_route"]["average"] = self.candidates[route_dict[0]]["P_route"]["average"]\
                + np.average(list(P_dict.values()))
        
                #print(TELlink, P_li_R,link_num)
            #コマンドによる数を合計
            self.effectness[COM_ID]["Check link number"] = self.effectness[COM_ID]["Check link number"] + link_num
            self.effectness[COM_ID]["Mean Probability of check"] = self.effectness[COM_ID]["Check link number"]/self.effectness[COM_ID]["candidate link number"]
    
    #あと表示結果は経路が短い順にした方が良いと思う
    def show_candidates(self):
        for key in self.candidates.keys():
            #telに関するものは飛ばす
            if (len(key)<2):
                continue
            elif key[0]!=self.human_select:
                continue
            elif not self.candidates[key]["COM"] and not self.candidates[key]["COM"]:
                continue
            print("Command",key[0],"(",self.sat.COM[key[0]].name, ") & Telemetry",\
                  key[1],"(", self.sat.TEL[key[1]].name, ") can verify following links\n",\
              "COMlink:",self.candidates[key]["COM"], "TELlink", self.candidates[key]["TEL"])
        #print("check those corresponding Telemetry")

    #デフォルト値使ってオーバーロードする
    def receive_selection(self, COM_ID=0):
        if not COM_ID:
            while(1):
                self.human_select = int(input("Please select Command above(input ID) >>"))
                #ここに想定してない入力をはじく処理必要
                if (self.human_select not in self.remainingCOM):
                    continue
                else:
                    self.show_candidates()
                    break
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
                #candidate update必要
                self.candidates.update(self.sat.find_check_COM(COM_ID))
                #ここでも集計し直す
                self.find_total_link(COM_ID)
                self.calculate_mean_check_link_number(COM_ID)
                self.count_COM_num_for_link(COM_ID)
                self.propagate_COM_effect(COM_ID)
                self.calculate_point(COM_ID)
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
        print("COM", COM_ID, self.sat.COM[COM_ID].name, self.effectness[COM_ID],self.negative_effect[COM_ID])
        
    #そのコマンドを打つとどうなるかを更新する
    #これはあくまでも可能性の更新．本当にそのような遷移をしたかは，テレメトリの結果に依存する．←これはどうやって実装する？
    def propagate_COM_effect(self,COM_ID):
        previous_compo_state = {}
        #ACTION
        if self.sat.COM[COM_ID].type == "ACTION":
            for target in self.sat.COM[COM_ID].target:
                compo = self.sat.compos[target["Component"]]
                previous_compo_state[compo.name] = copy.deepcopy(compo.Active)
                #電源操作系のコマンドはFunctionが空
                if not target["Function"]:
                    if self.sat.COM[COM_ID].Active and not compo.Active:
                        compo.Active = True
                        self.sat.COM_consume_power = compo.PowerConsumption
                    elif not self.sat.COM[COM_ID].Active and compo.Active:
                        compo.Active = False
                        self.sat.COM_consume_power = - compo.PowerConsumption
                    else:
                        self.sat.COM_consume_power = 0
                #コマンドがFunctionを持つ場合
                else:
                    for func in target["Function"]:
                        #コンポーネントはFunctionの名前をキーとして持つ
                        if self.sat.COM[COM_ID].Active and not compo.Function[func]["Active"]:
                            compo.Function[func]["Active"] = True
                            self.sat.COM_consume_power = compo.Function[func]["PowerConsumption"]
                        elif not self.sat.COM[COM_ID].Active and compo.Function[func]["Active"]:
                            compo.Function[func]["Active"] = False
                            self.sat.COM_consume_power = - compo.Function[func]["PowerConsumption"]
                        else:
                            self.sat.COM_consume_power = 0
            self.sat.update_Power_state()
            #もどす
            for name in previous_compo_state.keys():
                self.sat.compos[name].Active = previous_compo_state[name]
        #今は未実装なだけ，GETとかを実装する
        #GET
        elif self.sat.COM[COM_ID].type == "GET":
            
            return 0
    