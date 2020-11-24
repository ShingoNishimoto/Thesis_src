import copy
from collections import OrderedDict
from System import System
from CompoLink import Component
from CompoLink import Link

class Satellite(System):
    #各要素は辞書型で格納，アクセスするための参照をkeyにしておく,valueはオブジェクト
    def __init__(self, compos_df, links_df, COM_df, TEL_df, COM_type_dict):
        super().init_element(compos_df)
        self.compos = {x.name : x for x in [Component(x) for x in self.elements]}
        super().init_element(links_df)
        self.all_links = {x.ID : x for x in [Link(x) for x in self.elements]}
        self.COMlinks = {}
        self.TELlinks = {}
        self.classify_links()
        #print(self.TELlinks)
        #COMとTELだけpathの短い順に保持したい
        super().init_element(COM_df)
        COM_dict = OrderedDict({x.ID : x for x in [Command(x) for x in self.elements]})
        self.COM = OrderedDict(sorted(COM_dict.items(), key=lambda x:len(x[1].path)))
        #コマンドの種別の初期化
        for COM in self.COM.values():
            self.COM[COM.ID].init_COM_type(COM_type_dict[COM.name])
        super().init_element(TEL_df)
        TEL_dict = OrderedDict({x.ID : x for x in [Telemetry(x) for x in self.elements]})
        self.TEL = OrderedDict(sorted(TEL_dict.items(), key=lambda x:len(x[1].path)))
        #PCU or BATが持つ電力容量を衛星が管理
        self.RemainingPower = 0
        self.ConsumingPower = 0
        self.targetCOMpath = []
        self.targetTELpath = []
        self.COM_consume_power = 0
        
        
    #初期状態が必要．何のコマンドを受け取っていたのか？(どの機器がONになっていたのか？)ここの洗練化
    def init_state(self, ini_COMpist, all_compo_state_dict):
        self.initial_COM = ini_COMpist
        #コンポのstate追加
        for compo in self.compos.values():
            compo.update_state(all_compo_state_dict[compo.name])
        #衛星全体の電力状態を初期化
        self.TotalPower = self.compos["BAT"].state["PowerAmount"]["value"]
        self.update_Power_state()
        #最初だけ初期化後にコピー
        self.PreviousRemainPower = copy.deepcopy(self.RemainingPower)
    
    #これも提示するときと実際の選択に応じたアップデートで分ける必要がある．
    def update_Power_state(self):
        #全部に関して回すため，一回リセット
        self.RemainingPower = self.TotalPower #全体の容量を足す．ほんまは単位が別[mAh]なので足し合わせることはできないが，簡単のため今はこれでいい
        self.ConsumingPower = 0
        for compo in self.compos.values():
            #print(compo.name,compo.PowerConsumption,compo.Active)
            #衛星全体の電力状態を更新
            #Functionによる電力は見れていない
            if compo.Active:
                self.RemainingPower = self.RemainingPower - compo.PowerConsumption
                self.ConsumingPower = self.ConsumingPower + compo.PowerConsumption
            else:
                self.RemainingPower = self.RemainingPower
                self.ConsumingPower = self.ConsumingPower
            #print(compo,self.compos[compo].state)
        #print("remain",self.RemainingPower, "consumed", self.ConsumingPower)
            
    def classify_links(self):
        for compo in self.compos:
            for p_ID in self.all_links.keys():
                #deep copyしてるから別物
                if p_ID in self.compos[compo].COM_link:
                    self.COMlinks[p_ID] = copy.deepcopy(self.all_links[p_ID])
                if p_ID in self.compos[compo].TEL_link:
                    self.TELlinks[p_ID] = copy.deepcopy(self.all_links[p_ID])
    
    #targetとなるTEL ID, COM ID(これらはリスト)受け取って，そこから考える
    #これもほんまはコマンドとテレメトリの組み合わせのリストとして受け取りたい
    def find_target_path(self, targetTEL_ID, targetCOM_ID):
        self.targetTEL_ID = targetTEL_ID
        self.targetCOM_ID = targetCOM_ID
        #pathIDとして定義されていないものが入った時の対応がない
        #検証対象のパスをリストで取る．これだけだと複数あって中にかぶりが合った時に困る
        if not targetTEL_ID:
            self.targetTEL_ID = []
        else:
            targetTEL_paths = [j for j in [self.TEL[i].path for i in targetTEL_ID]]
        if not targetCOM_ID:
            self.targetCOM_ID = []
        else:
            targetCOM_paths = [j for j in [self.COM[i].path for i in targetCOM_ID]]
        
        #かぶりの解消と，階層構造をなくす操作が必要
        one_layer_targetTELpath = []
        for path in targetTEL_paths:
            self.down_demension(path, one_layer_targetTELpath)
        #被りなくして追加
        self.targetTELpath.extend(list(dict.fromkeys(one_layer_targetTELpath)))
        #COM
        #junctionを取得
        #listの同一にあるのがペアだと仮定している．入力の仕方としてどのやり方がきれいなのか考える．
        #どっちも影響するときはどうするん？やっぱりimpact TEL IDから見なあかんかもな
        #以下はコマンドがあるときの話
        if targetCOM_ID:
            junction = []
            for i in range(len(targetTEL_ID)):
                junction.extend(self.find_junction(targetTEL_ID[i], targetCOM_ID[i]))
                #print(junction[i].name)
                
            targetCOM_route = []
            for COM_ID in targetCOM_ID:
                one_layer_targetCOMpath = []
                targetCOM_path = self.COM[COM_ID].path
                self.down_demension(targetCOM_path, one_layer_targetCOMpath)
                for compo in junction:
                    self.trace_with_compo(compo, one_layer_targetCOMpath, targetCOM_route)
                    #print(targetCOM_route)
            self.targetCOMpath.extend(reversed(list(dict.fromkeys(targetCOM_route))))
            self.update_link_probability()
        #targetCOM_IDが特に指定されていない場合
        else:
            self.targetCOMpath = []
        print("targetTEL:",self.targetTELpath)
        print("targetCOM:",self.targetCOMpath)
        
    #各リンクの正常確率は事前に定義しておくものを初期値として考える．
    #ターゲットにならなかったものは全て1に更新する．
    def update_link_probability(self):
        for lID in self.COMlinks.keys():
            if lID not in self.targetCOMpath:
                self.COMlinks[lID].probability = 1
            #print(self.COMlinks[lID].probability)
        for lID in self.TELlinks.keys():
            if lID not in self.targetTELpath:
                self.TELlinks[lID].probability = 1
            #print(self.TELlinks[lID].probability)
    
    #テレメトリから不具合のトリガーとなったコマンドを探す場合
    #def find_triggerCOM
    
    #この時に確率の高いものだけを抽出し，抽出したものは消すようにすれば段階的探査ができる
    #こいつを使っているのはコマンド（テレメも）のパスの階層をなくすため
    def down_demension(self, path, one_layer_path):
        for link in path:
            #階層構造を馴らす,csvでくること前提になっている？
            self.recurrent_search(link,one_layer_path)
        #順番はどうするべきか考える．GSからの距離に対応してない
       # return one_layer_path
    
    def recurrent_search(self, link, one_layer_path):
        if (type(link) != list):
            one_layer_path.append(link)
            return 1
        #こっちに来たものはネストされていたもの
        #空判定
        elif (link):
            #popしてしまうと元が変更されてしまうのでdeepcopy
            link_for_pop = copy.deepcopy(link)
            p = link_for_pop.pop(0)
            one_layer_path.append(p)
            return self.recurrent_search(link_for_pop,one_layer_path)
        else:
            return 1
        
    #実際はここで与える順番として，持っているパスが短いものから行きたい．それが地上局に近いはずなので
    def search_TEL(self, TEL_ID):
        verify_candidates = {}
        #print("TELtarget:",self.targetTELpath)
        #各テレメトリのverify_linkを更新
        self.TEL[TEL_ID].find_check_TEL(self.targetTELpath)
        #受け渡す
        local_verify_candidate = {"TEL":self.TEL[TEL_ID].verify_linkID}
        self.get_propose_links((TEL_ID,), local_verify_candidate, verify_candidates)
        #リセット
        self.TEL[TEL_ID].verify_linkID = []
        return verify_candidates
                        
            
    #GETとACTIONの処理をちゃんと分けたほうがいい
    def find_check_COM(self, COM_ID):
        #初期化
        self.COM[COM_ID].verify_flag = 0
        self.COM[COM_ID].candidateTELnum = 0
        self.COM[COM_ID].candidate_TEL_ID = []
        if not self.targetCOMpath:
            return {}
        one_layer_COMlinks = []
        verify_candidates = {}
        #GETの対象テレメトリを下ろす
        if self.COM[COM_ID].type == "GET":
            self.set_TEL_availability(COM_ID)
                
        #各コマンドの経路のみを対象にしている
        self.down_demension(self.COM[COM_ID].path, one_layer_COMlinks)
        #print(self.COM[COM_ID].name, "'s one layer'", one_layer_COMlinks)
        for TEL_ID in self.COM[COM_ID].impact_TEL_ID:
            #不具合検知のきっかけとなった組み合わせはあてにならないので，飛ばす．
            #降りているかも確認．後から降りていないときは下ろすコマンドも合わせて考えられる用に修正する．
            if COM_ID in self.targetCOM_ID and TEL_ID in self.targetTEL_ID or not TEL_ID:
                continue
            #以下の実装はACTIONコマンドにしか適用できない
            #コマンドの経路の定義時にtargetのコンポまでの経路のみを作っておく．
            #そのコマンドがtarfetの状態を変化させるかどうかによって調べるか調べないかを見るようにする，
            #ACTIONは接続点を見つける．GETにも変化を及ぼすテレメトリがある．カウンタ系（これを別に種別として定義したほうが，今後の実装が楽そう）
            junction = self.find_junction(TEL_ID, COM_ID)
            if junction:
                #junctionから辿って状態変化を起こすペアの経路見つける．
                candidate_COMlinks = self.add_candidates(COM_ID,TEL_ID,junction,one_layer_COMlinks)
            #GETの場合の一部はループになっていないので別途定義する
            elif self.COM[COM_ID].type == "GET":
                #ここは一旦簡単に追加するだけにしておく．GETは一本道であるという仮定
                candidate_COMlinks = one_layer_COMlinks
                self.TEL[TEL_ID].find_check_TEL(self.targetTELpath)
            else:
                candidate_COMlinks = []
        #プラスアルファで経路内のコンポに入力がある場合はそれも考える．これは将来的に
            
            #状態を変化させないコマンドのcandidateは空
            if candidate_COMlinks:
                #影響テレメトリとの経路に対応するパスから検証ポートを探す
                for p_ID in candidate_COMlinks:
                    if p_ID in self.targetCOMpath:
                        self.COM[COM_ID].verify_linkID.append(p_ID)
            #print(self.COM[COM_ID].verify_linkID)
                
            
            local_verify_candidate = {"COM": self.COM[COM_ID].verify_linkID, "TEL":self.TEL[TEL_ID].verify_linkID}
            #print(local_verify_candidate)
            self.get_propose_links((COM_ID,TEL_ID), local_verify_candidate, verify_candidates)
            #print(verify_candidates)
            #verify linkがないやつは表示しない
            if (not self.COM[COM_ID].verify_linkID) and (not self.TEL[TEL_ID].verify_linkID):
                #print(self.COM[COM_ID].name, "&", self.TEL[TEL_ID].name, "empty")
                #print(COM_ID,TEL_ID)
                continue
            #確認の組み合わせがあるTELを集計
            elif TEL_ID not in self.COM[COM_ID].candidate_TEL_ID:
                #ここの信ぴょう性が低い
                self.COM[COM_ID].candidate_TEL_ID.append(TEL_ID)
                if not self.TEL[TEL_ID].checked_flag:
                    self.COM[COM_ID].verify_flag = 1
                    #引き出しの多さ
                    self.COM[COM_ID].candidateTELnum = self.COM[COM_ID].candidateTELnum + 1
          
            #今回の組み合わせによるものであることを示すため，一回リセットする
            self.COM[COM_ID].verify_linkID = []
            self.TEL[TEL_ID].verify_linkID = []
        #print(verify_candidates)
        #availabilityはリセット？
        #if self.COM[COM_ID].type == "GET":
        #    self.reset_TEL_availability(COM_ID)
        return verify_candidates
    
    def set_TEL_availability(self,COM_ID):
        for target in self.COM[COM_ID].target:
            self.TEL[target["TEL_ID"]].availability = 1
            #調べる対象に追加する．でもこのままやと経路がおかしいのか．．多分junctionが見つからない
            self.COM[COM_ID].impact_TEL_ID.append(target["TEL_ID"])
            
    def reset_TEL_availability(self,COM_ID):
        for target in self.COM[COM_ID].target:
            self.TEL[target["TEL_ID"]].availability = 0
            #調べる対象から消す．必要ないかもしれないし，他で変なことなるかも
            self.COM[COM_ID].impact_TEL_ID.pop(target["TEL_ID"])
    
    def add_candidates(self,COM_ID,TEL_ID,junction,one_layer_COMlinks):
        candidate_COMlinks = []
        for end_compo in junction: #一応junctionが複数あるかもしれないという仮定
            #print(end_compo.name)
            #そのコマンドが状態を変化させるのかを確認
            #電源操作だけのコマンドにはFunctionがない
            #initial_Commandのものは状態がすでに変化しているとして見るので，飛ばさないようにする
            if COM_ID not in self.initial_COM:
                if (not self.COM[COM_ID].target[0]["Function"]) and (self.COM[COM_ID].Active == self.compos[self.COM[COM_ID].target[0]["Component"]].Active):
                    break
                #コマンドがアクセスするFunctionと一致するものを調べる．コマンドがもつFunctionは一つに絞ったほうがいいかもしれない?
                elif  self.COM[COM_ID].target[0]["Function"]:
                    func = self.COM[COM_ID].target[0]["Function"][0]#取り合えず一つのFunctionの時のみ実装
                    if func in end_compo.Function.keys():
                        if self.COM[COM_ID].Active == end_compo.Function[func]["Active"]:
                            break
            #GSに達したら出る
            #roup見つかれば1，なければ0が返る
            if self.trace_with_compo(end_compo, one_layer_COMlinks, candidate_COMlinks):
                #print(candidate_COMlinks)
                #ループがあって組み合わせが初めて検証できる
                self.TEL[TEL_ID].find_check_TEL(self.targetTELpath)
                break
            else:
                continue
        return candidate_COMlinks
   
    #candidatesに追加していく．段階ごとのものを全て持つようにする？
    #選択肢表示の
    def get_propose_links(self, propose_action, verify_candidate_links, candidates):
        #今の所したの条件分岐は意味ないが，入れ方を今後返るかもしれないので．
        #TELのみのとき
        if(len(propose_action)<2):
            candidates[propose_action] = copy.deepcopy(verify_candidate_links)
        #COMとTELの組み合わせ
        else:#deepcopyしないといけない謎．．
            candidates[propose_action] = copy.deepcopy(verify_candidate_links)
        
    def find_junction(self, TEL_ID, COM_ID):
        junction = []
        ini_link = self.TEL[TEL_ID].path[0]
        for compo in self.compos.values():
            if ini_link in compo.TEL_link:
                #これだけでは本当にただのjunction．見つけたあとの判定でしっかりループになる経路のjunctionなのか判別しないといけない
                junction.append(compo) # listの方がいい？
        return junction
    
    #モデル生成の過程に関してもここを流用したいが難しそう．．
    def trace_with_compo(self, compo, one_layer_COMlinks, candidate_COMlinks):
        trace_candidate_COMlinks = copy.deepcopy(one_layer_COMlinks)
        if compo.name == "GS": #根元
            return 1 #何を返す？
        #コマンドの経路が分岐して合流することはないと考える．->あるよ．電源のとこ
        else:
            #まずこのコンポの前のパスを探す．コンポがもつポートは始点コンポが持つので．注意
            #このやり方ではダメ．複数パスの時に
            next_compo_name = " "
            #ここの探し方も辞書型なら直近のみを見れるのでは？
            #対象コマンドが持つコマンドリンクを均したものを対象にしている
            for COMlink_ID in trace_candidate_COMlinks:
                COMlink = self.COMlinks[COMlink_ID]
                #現コンポを持つリンクを探す
                if compo.name in COMlink.component:
                    next_compo_name = COMlink.component[0] \
                    if compo.name == COMlink.component[1] else COMlink.component[1]
                    next_compo = self.compos[next_compo_name]
                    flag = 0
                    #print("Temp next compo:",next_compo_name)
                    #ここまででnext compo仮ぎめ
                    for nCOMlink_ID in next_compo.COM_link:
                        if self.COMlinks[nCOMlink_ID].ID in trace_candidate_COMlinks \
                        and compo.name in self.COMlinks[nCOMlink_ID].component:
                            trace_candidate_COMlinks.remove(nCOMlink_ID)
                            candidate_COMlinks.append(nCOMlink_ID)
                            flag = True
                        else:
                            continue
                    if flag:
                        break
                    else:
                        #next compoの再探索が必要
                        next_compo_name = " "
                        continue
            #nothingのときはループがない→情報が返ってこないので検証の候補にできない
            if next_compo_name == " ":
                #print("nothing")
                return 0
            else:
                #print("next:",next_compo_name)
                return self.trace_with_compo(next_compo, trace_candidate_COMlinks, candidate_COMlinks)
        
    
    #検証済みかの確認を行うためのメソッド
    def check_links(self, target_path, links):
        target_linksID = []
        for p_ID in target_path:
            if not links[p_ID].valid:
                target_linksID.append(p_ID)
        return target_linksID


#固有なのはID
class Command(Satellite):
    def __init__(self, COM):
        self.ID = COM.ID
        #コマンドとテレメトリが持つmasterとなるpathは辞書が関係性を明確にできるのでいいかもしれない
        self.path = [COM.path]
        #pathの1列目以降は"_number"になっている．getattr()でアクセス
        for i in range(len(COM)-6):
            COM_attr = "_" + str(i+6)
            #print(COM_attr)
            compo = [int(i) for i in getattr(COM,COM_attr).split(',')] \
            if type(getattr(COM,COM_attr)) == str else getattr(COM,COM_attr)
            compo = 0 if compo == 0 else self.path.append(compo)
        self.name = COM.CommandName
        if type(COM.impact_TEL_ID)==str:
            self.impact_TEL_ID = [int(i) for i in COM.impact_TEL_ID.split(',')]
        else:
            self.impact_TEL_ID = [COM.impact_TEL_ID]
        self.candidate_TEL_ID = []
        self.verify_linkID= []
        self.verify_flag = 1 #verifyに使われる可能性があるかの判定
        self.candidateTELnum = 0
        #self.verify_TELlinkID= []
        #print(self.ID,":",self.path) #OK
        #self.init()
    
    def init_COM_type(self,type_dict):
        self.type = type_dict["type"]
        #compo, function, valueとかまとめて持つ
        self.target = type_dict["target"]
        #print(self.target)
        self.Active = type_dict["Active"]
        #print(self.target)
        #ACTIONコマンド
        
        #SET
        
        #GET
        
        
    #どんな形式で保持するのがいいのか考える．今の実装を考えるとリストにしないとめんどくさいが．
    def init(self, path_dict):
        #コマンドIDに応じて格納する処理？というか受け取るものを自分のIDのものだけにすればいい
        print(path_dict)
        
#固有なのはID
class Telemetry(Satellite):
    def __init__(self, TEL):
        self.ID = TEL.ID
        self.path = [TEL.path]
        #pathの1列目以降は"_number"になっている．getattr()でアクセス
        #offset = TEL.columns.get_loc('path')+2
        offset = 6
        for i in range(len(TEL)-offset):
            TEL_attr = "_" + str(i+offset)
            compo = [int(i) for i in getattr(TEL,TEL_attr).split(',')] \
            if type(getattr(TEL,TEL_attr)) == str else getattr(TEL,TEL_attr)
            compo = 0 if compo == 0 else self.path.append(compo)
        self.name = TEL.TelemetryName
        self.trigger = TEL.TransitionTrigger
        self.verify_linkID= []
        self.checked_flag = 0
        self.availability = TEL.Availability
    
    #targetTElpathが空なら終わる
    def find_check_TEL(self, targetTELpath):
        if not targetTELpath:
            return 0
        candidate_links = []
        #なんか必要やったが，名前以外の機能がないか確認
        super().down_demension(self.path, candidate_links)
        #print(self.name,"'s path:",candidate_links)
        #print("TELtarget:",targetTELpath)
        for p_ID in candidate_links:
            if p_ID in targetTELpath:
                self.verify_linkID.append(p_ID)
        #ここで更新されたパスを次に持ち込まないように情報を渡す必要がある
        #print(self.name, "'s verify links:", self.verify_linkID)