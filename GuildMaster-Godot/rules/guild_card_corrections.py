"""Corrections verified against the selected prints in the 2026-09-22 audit.

Installed after artwork/version selection, identically on client and server.
The audit's OCR is deliberately not used as executable rules or card wording.
"""


def install(ns):
    cards, heroes, royals = ns['CARDS'], ns['HERO_ARCHIVE'], ns['ACHIEVEMENTS']
    cards[1].update(draw=1, consume_piece=0, description='',
                    steps=[dict(op='consume_tiles', min=1, max=1, optional=True,
                                per=dict(draw=2))])
    cards[11]['steps'][0]['optional'] = True
    for card in cards.values():
        if card.get('printed_code') == 'A-080':
            card.update(draw=0, steps=[dict(op='purify', optional=True),
                dict(op='consume_tiles', min=1, max=3, optional=True, per=dict(gold=5)),
                dict(op='effect', effect=dict(draw=1))])
    cards[45]['conditional'][0]['effect']['gold_pro'] = 4
    cards[45]['conditional'][1]['effect']['gold'] = 8
    for cid, price in ((51,18),(57,11),(62,10),(121,7),(156,15),(158,15),(221,15)):
        cards[cid]['price'] = price
    cards[54]['steps'][0]['costs']['gold'] = 6
    for cid in (55,56,60):
        cards[cid]['action']['costs']['gold'] = 3
    cards[55]['gold_pro'] = 2
    for cid in (56,60,78):
        cards[cid]['pot'] = 1
    cards[57].update(point=2, action=dict(steps=[dict(op='pay_resource', resource='strength',
        min=1, max=3, per=dict(gold=5), optional=True)]),
        steps=[dict(op='purify', optional=True, otherwise=dict(steps=[dict(op='supply')]))])
    cards[58].update(gold_pro=0, civ=1)
    cards[62].update(gold_pro=0, str_pro=1)
    cards[62]['action']['costs'] = dict(strength=1)
    cards[63]['action']['gold'] = 5
    cards[64].update(gold_pro=3, point=2)
    cards[70]['scoring'][1]['threshold'] = 12
    cards[71]['scoring'][0]['threshold'] = 2
    cards[94]['steps'][0].update(optional=True)
    cards[96]['scaled'][0]['solo_max'] = 40
    cards[101]['strength'] = 1
    cards[117]['point'] = -4
    cards[128]['draw'] = 1
    cards[128]['triggers'][0]['effect']['gold'] = 3
    cards[165].update(consume_piece=1, costs={}, steps=[], affection=1)
    cards[193]['triggers'] = [dict(event='card_tags', condition=dict(any_tags=['civ','character']),
                                  effect=dict(steps=[dict(op='counter',count=1)]))]
    cards[194].update(tags=[], point=0)
    cards[200].update(tags=['civ'], point=1)
    cards[200]['action'] = dict(steps=[dict(op='attach_tile',min=1,max=2,per=dict(strength=1))])
    cards[201]['costs'] = dict(gold_pro=1)
    cards[221].update(draw=1, requirements={})
    royals['royal134']['requirement']['value'] = 4
    royals['royal134']['requirements']['heart'] = 4
    royals['royal134']['description'] = '好感度至少4，零件标记至少4。'
    royals['royal140']['point'] = 4
    for key, count in (('solo_normal_3',5),('solo_hard_3',4)):
        royals[key].update(requirement={}, requirements=dict(stat='pieces',value=count),
                           description='持有迷宫板块至少%s。' % count)

    heroes['hainie_red']['upgrade3'] = dict(gold=10,steps=[dict(op='achievement')])
    # This pre-action can consume the clicked card (or change the intended
    # action's costs/requirements). Let the player choose their main action
    # after it resolves instead of replaying a stale click.
    heroes['siren_white']['resume_first_action'] = False
    heroes['skadi_white']['points'] = 4
    heroes['ruby_white']['upgrade2'] = dict(gold_pro=2,str_pro=1,tags=['character'])
    heroes['ayaka_revised'].update(gold=34,draw=1,points=4,
        ability=dict(steps=[dict(op='branch',options=[
            dict(label='通常打出',effect=dict(steps=[dict(op='play')])),
            dict(label='支付1睿智：减5金币并免除额外费用',effect=dict(steps=[
                dict(op='play',discount=5,ignore_extra=True,costs=dict(wisdom=1))]))])]),
        upgrade3=dict(gold=10,wisdom=1,steps=[dict(op='draw_achievement_select',count=2,keep=1)]))
    heroes['elu_red'].update(passive={},triggers=[dict(event='explore',effect=dict(draw=1))])
    heroes['elu_red_b'].update(passive=dict(season_pre_action=True),triggers=[])
    for key in ('elu_red','elu_red_b'):
        heroes[key]['upgrade2']['draw'] = 1
        heroes[key].update(points=4,upgrade3=dict(steps=[
            dict(op='discard_gain',all_hand=True,resource='gold',per=3,optional=True),
            dict(op='extra_action')]))
    heroes['skadi_red']['upgrade2'].pop('tags',None)
    heroes['skadi_red']['points'] = 3
    heroes['ayaka_red_b']['upgrade3']['strength'] = 3
    heroes['melissa_red']['upgrade2']['strength'] = 1
    heroes['siren_red']['points'] = 3
    heroes['misha_red']['draw'] = 1
    heroes['misha_red']['upgrade2'].pop('gold_pro',None)
    heroes['misha_red']['upgrade2']['steps'] = [dict(op='supply')]
    heroes['misha_red']['passive']['final_extra_gold'] = 20
    heroes['shion_red'].update(points=4)
    heroes['shion_red']['upgrade3']['strength'] = 1
    heroes['alicia_red'].update(ability={},first_steps=[dict(op='reveal',count=2)])
    heroes['marta_white']['upgrade2'].pop('gold',None)
    heroes['marta_white']['upgrade2']['gold_pro'] = 5
    heroes['vee_black']['upgrade3'] = dict(steps=[dict(op='flip',max=2,optional=True,per=dict(strength=1))])
    for key in ('shuri_black','macaron_black'):
        heroes[key]['strength'] = 2
    heroes['macaron_black']['upgrade3']['steps'][0].update(optional=True,per={},stars_gold=5)
    heroes['horn_black']['upgrade3'] = dict(scaled=[dict(resource='gold',stat='extra_cost_cards',multiplier=5)])

    # These are implementation summaries, not purported verbatim transcriptions.
    summaries = {
        'hainie_red':'开局解锁“打出至少8张事件卡”的好感度格，无需满足事件卡数量条件；每获得1好感度，获得2力量。二级：力量产能+1。三级：获得10金币，然后可完成一张成就卡。',
        'ruby_white':'特别行动：打出事件，减免好感度与人物标记合计的金币。二级：金币产能2、力量产能1、人物标记1。三级：每个人物标记获得1秘药。',
        'ayaka_revised':'特别行动：打出事件，可支付1睿智，减5金币并免除额外费用。三级：抽2张未使用成就选1张，获得1睿智、10金币。',
        'elu_red':'成功探索后抽1张事件。二级：力量产能1、抽1牌、零件标记1。三级：可弃任意手牌，每张3金币，然后执行一个主要行动。',
        'elu_red_b':'每季起始玩家行动前，先执行一个主要行动（单人无效）。二级：力量产能1、抽1牌、零件标记1。三级：可弃任意手牌，每张3金币，然后执行一个主要行动。',
        'misha_red':'开局抽1牌并获得普通迷宫板块。二级：力量产能2、生活标记1、普通迷宫板块1。三级：结束阶段末获得20金币并执行一个主要行动；单人为第6轮行动阶段末。',
        'alicia_red':'首次行动前公开两块迷宫。探索此前已公开的迷宫，金币费用减5。二级：力量产能1、零件标记1。三级：力量2，再执行一个主要行动。',
        'vee_black':'特别行动：据点基础费用15金币，每个零件标记减3，最低0；相邻追加费照付。三级：可将最多两张正面事件翻至背面，每张获得1力量。',
        'macaron_black':'首次行动前公开两块迷宫。探索每降低1瘴气，获得2金币和1金币产能，每个行动最多3次。三级：可支付最多两块迷宫，每颗星获得5金币，然后抽1牌。',
        'sif_black':'特别行动：打出一张事件，每个持有迷宫板块减3金币。',
        'bell_black':'特别行动：将一块持有迷宫板块放在看板娘上，获得8金币；板块有名声时再获得1力量。',
        'horn_black':'支付费用时，秘药与持有迷宫板块可等量互相替代。三级：每张已打出且有额外费用的正面事件，获得5金币。',
    }
    for key, text in summaries.items():
        heroes[key]['description'] = text
    for item in ns['HERO_GALLERY'].values():
        hero = heroes.get(item.get('hero'))
        if hero:
            item['description'] = hero.get('description','')
    from guild_new_content import QUESTS, PROLOGUES
    # Phase B（2026-10）：序章卡改用純掃描面（pack/XG_<格>）
    _story_cells = {0: 15, 1: 9, 2: 12, 3: 2, 4: 11, 5: 10, 6: 1, 8: 8, 9: 14, 10: 3, 12: 6, 13: 4, 16: 5, 18: 7, 20: 13}
    for _pid, _cell in _story_cells.items():
        if _pid in PROLOGUES:
            PROLOGUES[_pid]['source'] = 'pack/XG_%d' % _cell
    QUESTS[24]['name'] = '二星以上板块1'
    # Phase B2（2026-10）：冒險者的慶典擴充序章改純掃描面（pack/XG2_<格>）
    _story_cells2 = {15: 1, 19: 2, 17: 3}
    for _pid, _cell in _story_cells2.items():
        if _pid in PROLOGUES:
            PROLOGUES[_pid]['source'] = 'pack/XG2_%d' % _cell
    PROLOGUES[16]['effect']['steps'][-1]['retry_hole'] = True
    renamed = {}
    for cid, (title, text) in PRINTED_EVENT_TEXT.items():
        card = cards[cid]
        renamed[card['name']] = title
        card.update(name=title, printed_text=text)
    # Legacy special-card references used names; keep their identity intact.
    def update_special(value):
        if isinstance(value,dict):
            if value.get('initial_special') in renamed:
                value['initial_special'] = renamed[value['initial_special']]
            if value.get('op') == 'return_special' and value.get('name') in renamed:
                value['name'] = renamed[value['name']]
            for child in value.values():
                update_special(child)
        elif isinstance(value,list):
            for child in value:
                update_special(child)
    update_special(heroes)
    for item in ns['CARD_GALLERY'].values():
        card = cards.get(item.get('id'))
        if card:
            item.update(name=card['name'],printed_text=card.get('printed_text',''))

    # Phase A（2026-10 新印面校對）：城市擴充 9 張重新啟用，並依新印面改為「即時獲得」。
    city_updates = {
        'A-109': dict(available=True, special=False, archived_print=False, unavailable_reason=''),
        'A-110': dict(available=True, special=False, archived_print=False, unavailable_reason='',
                      str_pro=0),
        'A-111': dict(available=True, special=False, archived_print=False, unavailable_reason='',
                      gold_pro=0, str_pro=0, gold=2, strength=1,
                      steps=[dict(op='purify', optional=True),
                             dict(op='all', effect=dict(strength=1))]),
        'A-112': dict(available=True, special=False, archived_print=False, unavailable_reason='',
                      gold_pro=0, gold=3),
        'A-113': dict(available=True, special=False, archived_print=False, unavailable_reason='',
                      str_pro=0),
        'A-114': dict(available=True, special=False, archived_print=False, unavailable_reason='',
                      gold_pro=0, gold=2),
        'A-115': dict(available=True, special=False, archived_print=False, unavailable_reason='',
                      gold_pro=0, gold=5),
        'A-116': dict(available=True, special=False, archived_print=False, unavailable_reason='',
                      steps=[dict(op='flip', min=1, max=1, optional=True)]),
        'A-117': dict(available=True, special=False, archived_print=False, unavailable_reason=''),
    }
    for card in cards.values():
        upd = city_updates.get(card.get('printed_code'))
        if upd:
            card.update(**upd)
        if card.get('printed_code') == 'D-002':
            card.update(gold_pro=0, gold=4)
        if card.get('id') == 337 or card.get('name') == '情報販子琪修':
            card.update(printed_code='E-025', image_path='pack/11_1',
                        source='pack/11_1', new_art=True,
                        gold=4, gold_pro=0, draw=3,
                        ui_summary='规则说明：费用16金币；条件：已打出4张以上事件卡；打出时：金币+4、抽3张事件卡；获得标记：商业、人物；终局每持有2张有常时效果的事件卡获得1点名声（1+声望）')


    # ??????????2026-10???-15 ???
    FESTIVAL_CODES = {320:'A-118',321:'A-119',322:'A-120',323:'A-121',324:'A-122',
        325:'A-123',326:'A-124',327:'A-125',328:'A-126',329:'A-127',330:'A-128',
        331:'B-026',332:'B-027',333:'B-028',334:'D-014',335:'D-015',336:'D-016',
        337:'E-025',338:'E-026'}
    for _cid, _code in FESTIVAL_CODES.items():
        if _cid in cards:
            cards[_cid]['printed_code'] = _code
            cards[_cid]['expansion'] = 'festival_events'


    # 王權條件修正（2026-10 成就卡校對）
    ROYAL_FIX = {'royal133': {'requirements': {'any': [{'tags': {'civ': 5}}, {'tags': {'gold': 5}}, {'tags': {'scrap': 5}}]}}, 'royal138': {'requirements': {'played': 12}}, 'royal154': {'requirements': {'heart': 5, 'stat': 'earned_achievements', 'value': 1}}}
    for _key, _upd in ROYAL_FIX.items():
        if _key in royals:
            royals[_key].update(_upd)


# Manually checked titles and verbatim excerpts; blank text means no transcription.
PRINTED_EVENT_TEXT = {1: ('3.5t 貨車殘骸', '你可以支付 1 個迷宮板塊，藉此從牌庫抽取 2 張事件卡，並將其加入手牌。'),
 2: ('偶像出道', '【文明值 +1】'),
 3: ('公會的偶像', '【文明值 +1】'),
 4: ('迷宮前公會分店', ''),
 5: ('公會聯絡簿', '交換日記'),
 6: ('哥布林洞窟', '緊急任務\n獲得 1 個空白的迷宮板塊（從供應區拿取）。\n所有玩家（包含自己）【金幣生產量〔金幣生產量圖示〕+2】。'),
 7: ('混混少年團', 'C 級冒險者小隊\n若「文明值〔文明圖示〕」在 4 以下，則從牌庫抽取 1 張事件卡，將其加入手牌。'),
 8: ('火蜥蜴大澡堂', '【文明值 +1】'),
 9: ('導入輪班制', '你的「可派遣冒險者」方框中，每有 1 個未使用的冒險者標記，就獲得 3 個金幣〔金幣圖示〕。'),
 10: ('廢品區管理', ''),
 11: ('負離子產生器', '你可以選擇 1 個「深淵洞穴」板塊並將其淨化。\n【文明值 +1】'),
 12: ('金屬粉碎者', 'B 級冒險者小隊\n若「文明值〔文明圖示〕」在 4 以下，則你獲得 1 個戰力〔戰力圖示〕。'),
 13: ('惡魔之實', '【文明值 +1】'),
 14: ('異世界的桌遊', ''),
 15: ('異世界雜貨店', '○家便利商店\n你可以將 1 個未使用的冒險者標記放在此卡上，藉此獲得等同〔10＋商業〔商業圖示〕標籤數〕數量的金幣〔金幣圖示〕。\n【文明值 +1】'),
 16: ('異世界時裝秀', '從你的個人圖板選擇 1 個「好感度〔好感度圖示〕」標籤，並將其解放。\n【文明值 +1】'),
 17: ('異世界魔王討伐紀錄', '就是輕小說之類的東西'),
 18: ('三姑六婆聯合', '冒險者 …？\n你可以棄掉 1～5 張手牌，藉此從牌庫抽取等同棄掉張數的事件卡，並將其加入手牌。'),
 19: ('最前線魔物研究所', 'FRONTLINE LABORATORY\n執行 1 次「據點化」\n【文明值 +1】'),
 20: ('死靈王的大軍團',
      '緊急任務\n遊戲結束時，你每打出 1 張有〔戰力支付圖示〕符號（可以用戰力代替金幣支付該卡的打出費用）的事件卡，就獲得 2 點名聲。（包含此卡）\n所有玩家（包含自己）獲得 1 個秘藥〔秘藥圖示〕。'),
 21: ('開發手壓式抽水器', '【文明值 +1】'),
 22: ('看板娘的威壓', ''),
 23: ('懸賞怪物的通緝令', 'WANTED!\n選擇 2 個面朝下的迷宮板塊（不可選擇魔王板塊）並將其翻面。'),
 24: ('充滿心意的禮物', '從你的個人圖板選擇 1 個「好感度〔好感度圖示〕」標籤並將其解放。'),
 25: ('開發新型馬車', '獲得等同〔5＋生活〔生活圖示〕標籤數＋商業〔商業圖示〕標籤數〕數量（包含此卡）的金幣〔金幣圖示〕。\n【文明值 +1】'),
 26: ('新人教育制度', '你可以將 1 個未使用的冒險者標記放在此卡上，並藉此獲得 3 個戰力〔戰力圖示〕。'),
 27: ('深紅甲殼城', 'CRIMSON CASTLE\n執行 1 次「據點化」\n因這張卡片的效果執行「據點化」時，將相鄰該據點的面朝下迷宮板塊（魔王板塊除外）全部翻面。'),
 28: ('異世界料理教室', ''),
 29: ('皇家女僕部隊', 'ROYAL MAIDRION\n從以下兩個效果中擇一發動：\n・執行 1 次「據點化」。\n・獲得 1 個空白的迷宮板塊（從供應區拿取），並將【戰力生產量〔戰力生產量圖示〕+1】。'),
 30: ('機關大門', '選擇並獲得 1 個寶物板塊。\n【文明值 +1】'),
 31: ('宮殿裡的舞會', ''),
 32: ('極彩爆裂砲彈', ''),
 33: ('古代的食譜', '【文明值 +1】'),
 34: ('富商的邀請函', ''),
 35: ('朱紅色之門連綿的道路',
      '千本鳥居\n你可以選擇 1 個「深淵洞穴」板塊並將其淨化。\n你可以支付 1～3 個迷宮板塊，每支付 1 個板塊就獲得 5 個金幣〔金幣圖示〕。\n從牌庫抽取 1 張事件卡，並將其加入手牌。'),
 36: ('有精靈棲息的泉水', '你可以支付 1 個迷宮板塊，藉此獲得 1 個秘藥〔秘藥圖示〕。\n你可以棄掉 2 張手牌，藉此獲得 1 個秘藥〔秘藥圖示〕。'),
 37: ('神秘的水瓶', ''),
 38: ('研究人造深淵', '獲得 1 個「白框深淵洞穴」板塊（從供應區拿取）。\n【文明值 +1】'),
 39: ('水靈的小房間', '沖水馬桶\n【文明值 +1】'),
 40: ('仰望星空', ''),
 41: ('占卜師的帳篷', ''),
 42: ('攻破紀念祭', ''),
 43: ('深淵砲', ''),
 44: ('開拓邊境交易道路', ''),
 45: ('冒險者諮詢櫃台',
      '請問有什麼煩惱呢？\n'
      '若「文明值〔文明圖示〕」在 4 以下，則你的【金幣生產量〔金幣生產量圖示〕+4】。\n'
      '若「文明值〔文明圖示〕」在 5 以上，則你獲得等同〔8＋商業〔商業圖示〕標籤數〕數量（包含此卡）的金幣〔金幣圖示〕。'),
 46: ('速成露天浴場', ''),
 47: ('迷宮攻略RTA', ''),
 48: ('有效利用迷宮瘴氣', ''),
 49: ('龍墜少女', ''),
 50: ('群狼軍勢', ''),
 51: ('公會的拌嘴搭檔', '越吵感情越好\n你的看板娘每次升級時，就獲得 2 個戰力〔戰力圖示〕。'),
 52: ('暗影客', ''),
 53: ('完美默契', '你們快去結婚啦\n你每獲得 1 張成就卡，就獲得 3 個金幣〔金幣圖示〕。'),
 54: ('驛站的集會', '你每獲得 1 個「商業〔商業圖示〕」標籤，就獲得 2 個金幣〔金幣圖示〕。\n你可以支付 6 個金幣〔金幣圖示〕，藉此獲得 1 個空白的迷宮板塊（從供應區拿取）。'),
 55: ('青汁飲料機', '《特殊行動》\n支付 3 個金幣〔金幣圖示〕，並獲得 1 個秘藥〔秘藥圖示〕。'),
 56: ('婆婆的藥店', '《特殊行動》\n支付 3 個金幣〔金幣圖示〕，並獲得 1 個秘藥〔秘藥圖示〕。'),
 57: ('水晶墓碑',
      '《特殊行動》\n'
      '你可以支付 1～3 個戰力〔戰力圖示〕來獲得金幣〔金幣圖示〕，每支付 1 個戰力〔戰力圖示〕，就獲得 5 個金幣〔金幣圖示〕。\n'
      '你可以選擇並淨化一個「深淵洞穴」板塊。若不執行則改為獲得一個空白的迷宮板塊（從供應區拿取）。'),
 58: ('異世界的技術', ''),
 59: ('異世界電台', ''),
 60: ('特別收購稀有素材', '《特殊行動》\n支付 3 個金幣〔金幣圖示〕，並獲得 1 個秘藥〔秘藥圖示〕。'),
 61: ('古代魔像的墳墓', ''),
 62: ('和礦山妖精比酒量', '《特殊行動》\n支付 1 個戰力〔戰力圖示〕並執行 1 次「據點化」。然後將此卡翻面。'),
 63: ('蒸餾酒', '《特殊行動》\n支付 1 個秘藥〔秘藥圖示〕，並獲得等同〔5＋商業〔商業圖示〕標籤數〕數量的金幣〔金幣圖示〕。'),
 64: ('異世界拉麵食堂', ''),
 65: ('老舊的放映機', ''),
 66: ('聖女親衛隊', ''),
 67: ('迷宮開拓村', ''),
 68: ('吟遊詩人的傳唱', ''),
 69: ('設立冒險者學校', ''),
 70: ('迷宮祕寶館', '遊戲結束時，若你持有 5 個以上的「廢品〔廢品圖示〕」標籤，就獲得 2 點名聲；若你打出 12 張以上的事件卡，就獲得 2 點名聲。'),
 71: ('流浪商隊', '遊戲結束時，若你持有 2 個以上的「人物〔人物圖示〕」標籤，就獲得 2 點名聲；若你持有 5 個以上的「商業〔商業圖示〕」標籤，就獲得 2 點名聲。'),
 72: ('暗中保護皇女隊', ''),
 73: ('進擊的騎士公主', ''),
 74: ('聖女的寵愛', ''),
 75: ('與大賢者的盟約', ''),
 76: ('細緻的行商網路', ''),
 77: ('異界穿梭者 庫姬', ''),
 78: ('夏爾洛特 皇女', ''),
 79: ('騎士公主 甘娜許', ''),
 80: ('球型關節少女', ''),
 81: ('狼人女王', ''),
 82: ('聖女 馬卡龍', ''),
 83: ('大賢者 普雷切爾', ''),
 84: ('大魔導 海瑟', ''),
 85: ('傳奇旅行商人 費蕾茲', ''),
 86: ('勇者 蘿謝特', ''),
 87: ('流浪魔女 歐貝拉', ''),
 88: ('鬼神格拉尼提', ''),
 89: ('實習召喚士安雲', ''),
 90: ('司書 普拉琳', ''),
 91: ('精靈巫女阿瑪雷特', ''),
 92: ('木工大匠 加蕾特', ''),
 93: ('天眼 瑪特莉奴', ''),
 94: ('偉大的治癒師戚風', ''),
 95: ('史萊姆女王來襲', ''),
 96: ('毛茸茸園區開幕', '獲得等同你〔金幣生產量〔金幣生產量圖示〕−20〕的金幣〔金幣圖示〕（單人模式時至多 40〔金幣圖示〕）。\n若此卡打出時經過費用減免（包含追加費用），則將此卡翻面。'),
 97: ('花之妖精艾克萊兒', ''),
 98: ('吸血皇女格雷茲', ''),
 99: ('被詛咒的妖狐的封印', ''),
 100: ('真・龍墜少女', ''),
 101: ('絲卡蒂傭兵團', ''),
 102: ('蒼銀大要塞', ''),
 103: ('完美默契', '你們快去結婚啦\n你每獲得 1 張成就卡，就獲得 3 個金幣〔金幣圖示〕。'),
 104: ('老舊的放映機', ''),
 105: ('異界穿梭者 庫姬', ''),
 106: ('大賢者 普雷切爾', ''),
 107: ('惡魔的低語', ''),
 108: ('朱紅色之門連綿的道路',
       '千本鳥居\n你可以選擇 1 個「深淵洞穴」板塊並將其淨化。\n你可以支付 1～3 個迷宮板塊，每支付 1 個板塊就獲得 5 個金幣〔金幣圖示〕。\n從牌庫抽取 1 張事件卡，並將其加入手牌。'),
 109: ('研究人造深淵', '獲得 1 個「白框深淵洞穴」板塊（從供應區拿取）。\n【文明值 +1】'),
 110: ('深淵砲', ''),
 111: ('迷核實驗場', ''),
 112: ('迷宮大變動', ''),
 113: ('鬼神格拉尼提', ''),
 114: ('精靈巫女阿瑪雷特', ''),
 115: ('與盜賊公會的合作體制', ''),
 116: ('飛龍商標的貨運', ''),
 117: ('不治之症', ''),
 118: ('魔物料理', ''),
 119: ('迷宮城塞三勇士', ''),
 120: ('老練的分解師傅', ''),
 121: ('驚喜派對', ''),
 122: ('DEADLINE PARADE', ''),
 123: ('狹縫圖書館', ''),
 124: ('那天的誓言', ''),
 125: ('公會倉庫大掃除', ''),
 126: ('眼鏡追尋者', ''),
 127: ('毛茸茸天堂', ''),
 128: ('開發異世界甜點', ''),
 129: ('異世界技術解析小組', ''),
 130: ('命運的相遇', ''),
 131: ('飛天三笨蛋', ''),
 132: ('消費合作社', ''),
 155: ('兩人一起出門', ''),
 156: ('與武器工房的專屬契約', ''),
 157: ('被遺忘的女神像', ''),
 158: ('與魔術士公會聯手', ''),
 159: ('進口魔石', ''),
 160: ('魔導城奧蘿拉', ''),
 161: ('魔導通信網路', ''),
 162: ('魅惑的美乃滋', ''),
 163: ('無詠唱魔法的研究', ''),
 164: ('史萊姆異常增殖', ''),
 165: ('史萊姆商標的化妝品工房', '【文明值 +1】\n從你的個人圖板選擇 1 個「好感度〔好感度圖示〕」標籤，並將其解放。'),
 166: ('和平締結者', ''),
 167: ('榮光女王大飯店', ''),
 168: ('魔女的錫杖', ''),
 169: ('牛頭怪的守門人', ''),
 170: ('擬餌釣', ''),
 171: ('惡魔的低語', ''),
 172: ('異世界人的痕跡', ''),
 173: ('魔物 café', ''),
 174: ('迷核實驗場', ''),
 175: ('迷宮掃地機器人', ''),
 176: ('迷宮小街', ''),
 177: ('迷宮大變動', ''),
 178: ('勇者之劍的傳說', ''),
 179: ('梟之眼', ''),
 180: ('女孩的手做料理', ''),
 181: ('公會本部大改建', ''),
 182: ('炸彈特攻隊', ''),
 183: ('討伐芬里爾', ''),
 184: ('異世界連環畫工作室', ''),
 185: ('家事妖精的祝福', ''),
 186: ('極大淨化魔法的儀式', ''),
 187: ('成為劍術道場的後援', ''),
 188: ('帶來詛咒武器', ''),
 189: ('開發精靈蒸氣機構', ''),
 190: ('露天教室', ''),
 191: ('灰白城堡和小路裡的天空', ''),
 192: ('迷宮監視塔', ''),
 193: ('取暖用桌子',
       '常時效果\n'
       '每當你獲得有「生活〔生活圖示〕」和／或「人物〔人物圖示〕」標籤的事件卡時，就在此卡上放置 1 點數字標記。\n'
       '獲得名聲\n'
       '遊戲結束時，在此卡上每有 1 點數字標記，就獲得 1 點名聲（至多10點）。\n'
       '打出時效果\n'
       '若在第一輪打出，則獲得 5 個金幣〔金幣圖示〕。'),
 194: ('貴族的贊助', ''),
 195: ('大魔導的隨意妄為', ''),
 196: ('迷宮七大不可思議', ''),
 197: ('發現迷宮升降機', ''),
 198: ('迷宮寶石商', ''),
 199: ('與隱密一族的交流', ''),
 200: ('撿到小幻獸', ''),
 201: ('欠債生活', ''),
 202: ('假結婚', ''),
 203: ('東方的刀匠', ''),
 204: ('迷宮導遊', ''),
 205: ('迷宮地圖工匠', ''),
 215: ('無言的要求', ''),
 216: ('迷宮美食大賽', ''),
 217: ('建立迷宮品牌', ''),
 218: ('歡迎來到迷宮酒館！', ''),
 219: ('開設迷宮魔草園', ''),
 220: ('迷宮魔物異常增殖', ''),
 221: ('投資煉金術公會', ''),
 222: ('瘴氣溫泉', ''),
 223: ('海怪危機', ''),
 224: ('廢人化靠枕', ''),
 225: ('改善睡眠環境', ''),
 226: ('聖女到來', ''),
 227: ('聖水庫存過剩', ''),
 228: ('蒼銀大要塞', ''),
 229: ('地底湖度假行', ''),
 230: ('燈火通訊', ''),
 231: ('夢想已久的 My Home', ''),
 232: ('謎之科幻槍', ''),
 233: ('一夜城', ''),
 234: ('榮耀的黎明', ''),
 235: ('開發永動機', ''),
 236: ('王族視察迷宮', ''),
 237: ('壞掉的手機', ''),
 238: ('發掘出奇怪的石碑', ''),
 239: ('強行探索', ''),
 240: ('銀色的圓盤', ''),
 241: ('有效率的魔力訓練法', ''),
 302: ('聖女的遺痕', ''),
 320: ('勇敢行者', ''),
 321: ('與運輸公會的合作', ''),
 322: ('巨獸貝希摩斯的覺醒', ''),
 323: ('討伐礦石獸', ''),
 324: ('侵占救援物資', ''),
 325: ('方舟遺跡', ''),
 326: ('意外邂逅', ''),
 327: ('魔獸的生態調查', ''),
 328: ('開發魔法爐', ''),
 329: ('惡魔羽毛筆', '從牌庫頂翻開2張卡片，選擇其中1張，並使用所選卡「打出時效果」當作是此卡打出時效果。之後，將翻開的卡片丟入棄牌堆。'),
 330: ('迷宮時鐘', '執行一個額外行動。此時，若選擇「探索」，所需的必要成本-10。此時，若選擇「Pass」，則獲得10金幣，將看板娘翻面，本季無法再行動。'),
 331: ('加蕾特建築公司', '執行「據點化」時，因相鄰據點產生的追加費用-5。'),
 332: ('能量飲料 Bring Feather', '遊戲「結束階段」結束時，獲得10枚金幣，並再執行一次「主要行動」。'),
 333: ('積分卡', '每次你打出成本個位數為「0」或「5」的事件卡，獲得2枚金幣。'),
 334: ('Phrase百貨', '遊戲結束時，指定一張已經打出的事件卡，獲得與該卡「名聲」相同數量的「名聲」（包含因「獲得名聲」或「失去名聲」效果而變動的數值）。'),
 335: ('精靈的居住園地', ''),
 336: ('魔力工業聯合體', '遊戲結束時，如果你的金幣產量達到「30」以上，獲得2點名聲。持有6個以上的迷宮板塊，再獲得2點名聲。選擇一個「深淵洞穴」板塊淨化。'),
 337: ('情報販子琪修', ''),
 338: ('劍聖阿茲姬', '執行一次「探索」，此時，在計算成本時，目標板塊視為普通迷宮板塊。(BOSS除外，此效果可探索「深淵洞穴」)')}
