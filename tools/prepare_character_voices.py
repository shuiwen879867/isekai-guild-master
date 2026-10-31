"""Author original Chinese character cues and map every playable print to audio.

The supplied Shion recording remains untouched. Other voices are disclosed
synthetic performances with character-specific writing, pace and pitch.
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'GuildMaster-Godot-src'
sys.path.insert(0, str(ROOT / 'guild-server'))
from guild_content import HEROES

EVENTS = ['intro','select-white','select-red','close-first','close-last','close-shop','settle-win','settle-lose']


def profile(name, voice, rate, pitch, style, lines):
    rows = [line.strip().split('|') for line in lines.strip().splitlines()]
    assert len(rows) == len(EVENTS) and all(len(row) == 2 for row in rows), name
    return dict(name=name, speaker=voice, rate=rate, pitch=pitch, style=style, lines=dict(zip(EVENTS, rows)))


PROFILES = {
 'bai': profile('白','zh-CN-XiaoyiNeural','-8%','-10Hz','冷静、简洁，重视效率与情报', '''
我是白。情报已经整理好了。|公会长，按计划行动吧。
无用的情报，也能换来收益。|账目交给我，你来决定下一步。
零件和力量，我都不会浪费。|这次，就用行动证明判断。
先休息。领先一步，也要留有余地。|我先闭店，下一季再见。
最后一笔，也核对完了。|所有人都回来了，我也该收工了。
本季记录，整理完毕。|到此为止，准备下一季。
判断正确。是大家共同的胜利。|结果和计划一致，做得很好。
记录下原因，下次修正。|只是这一次失利，计划还会继续。'''),
 'hainie': profile('海涅','zh-TW-HsiaoChenNeural','+4%','+8Hz','亲切、细致，擅长照顾公会伙伴', '''
我是海涅，很高兴能和你一起经营公会。|公会长，需要帮忙的时候，随时叫我。
把开支省下来，就能照顾更多伙伴。|生活、商贸和工坊，都要安排妥当。
你的信任，就是我的力量。|伙伴们的心意，我都收到了。
今天就让我先打烊吧，大家也别太累。|我先回去准备晚餐，你们要注意安全。
都回来了吗？那我们也关门吧。|最后一位伙伴平安归来，真好。
辛苦了，来喝杯热茶吧。|今天也顺利结束了，早点休息。
太好了，大家的努力都有回报。|能和你们分享胜利，我很开心。
不要难过，我们还有彼此。|先好好休息，明天我还会陪着你。'''),
 'misha': profile('米夏','zh-CN-XiaoyiNeural','+11%','+16Hz','活泼、爽朗，喜欢豪爽投资与探险', '''
米夏来啦！今天也要大干一场！|公会长，带我去看看新的迷宫吧！
大生意当然要认真做！|别舍不得投入，好东西值得！
背包收拾好了，随时都能出发！|再远的迷宫，我也想去看看！
我先去休息，明天还要跑第一！|今天先到这里，体力也要留着嘛。
终于轮到我收工啦！|大家都走了？那我也不客气了！
今天收获不错，回家！|打烊啦，冒险故事留到明天讲！
赢啦！这下可要好好庆祝！|看到了吗？咱们公会就是这么厉害！
差一点点！下次我一定追上！|别泄气，再冒险一次就好啦！'''),
 'sofia': profile('索菲亚','zh-TW-HsiaoYuNeural','-4%','+2Hz','温柔、稳重，重视居民与领地建设', '''
我是索菲亚，愿这里成为大家的归处。|公会长，让我们慢慢建立可靠的家园。
安稳的生活，也是一种力量。|先照顾好日常，繁荣自然会来。
每一处据点，都要让人安心。|让我们的领地，彼此连接起来。
我先回去照看居民，辛苦你们了。|趁天色还早，我先去安排休息。
最后的灯，也该熄下了。|大家都平安回来，我就放心了。
今天的事务已经办妥。|好好休息，我们的家园还在成长。
这份繁荣，属于每一位伙伴。|谢谢你，让我们的家园更加美好。
家园还在，希望就不会消失。|我们慢慢重建，下一次会更好。'''),
 'alicia': profile('艾莉西亚','zh-CN-XiaoxiaoNeural','+6%','+4Hz','自信、机敏，商贸与侦察并重', '''
艾莉西亚，已经准备好合作了。|公会长，机会总是留给眼光敏锐的人。
让每一条商路，都带来回报。|交易的时机，我替你看着。
先看清迷宫，再决定出发。|我会把前路的情报带回来。
我先撤了，好的生意也需要休息。|本季的机会已经抓住，先打烊吧。
最后一笔交易，成交。|收尾也要利落，走吧。
本季业务结束，下次再合作。|帐算清了，安心休息吧。
漂亮，这份成绩很有说服力。|我们的眼光，果然没错。
判断有偏差，再找新的机会。|市场会变，下一次轮到我们。'''),
 'skadi': profile('丝卡迪','zh-CN-XiaoyiNeural','-7%','-18Hz','沉着、果断，佣兵领队的干练语气', '''
丝卡迪，接受委托。|公会长，说出你的目标。
金币不够，就用力量开路。|把资源交给我，不会白白损耗。
佣兵团已集结，等待指令。|目标确定了，就别犹豫。
本季任务完成，我先撤退。|先保存战力，后面还有硬仗。
最后一队也回来了，收队。|确认全员安全，结束行动。
行动到此为止，整备装备。|休息也是任务的一部分。
任务完成。你指挥得不错。|胜利属于守住阵线的人。
撤退，保存有生力量。|失败要记住，下次别再重复。'''),
 'ruby': profile('露比','zh-CN-XiaoxiaoNeural','+10%','+20Hz','明快、热情，珍视羁绊与伙伴', '''
我是露比！一起把公会变得热热闹闹吧！|公会长，有新伙伴要来了吗？
大家的心意，会帮我们打开机会！|有伙伴在，什么困难都能一起解决！
新的挑战，也要大家一起上！|只要同心协力，就没什么好怕的！
我先去招呼伙伴们啦！|今天先休息，明天也要元气满满！
最后一个伙伴也回来了呢！|那就一起关门，一起回家！
今天也认识了好多朋友！|打烊啦，记得和大家说晚安！
赢啦！我要把这份快乐告诉每个人！|大家一起努力，真的做到了！
别难过，我会一直为你加油！|我们一起再试一次，好不好？'''),
 'peria': profile('皮耶利亚','zh-TW-HsiaoChenNeural','+7%','+18Hz','轻盈、耐心，教学妖精般的鼓励', '''
皮耶利亚来帮忙啦！我们一步一步来。|公会长，不懂的地方尽管问我。
先看看情报，再选喜欢的计划吧！|开局准备好，后面就会轻松很多。
第一季的准备，就让我来吧！|认真安排生产，公会会慢慢成长。
先闭店也没关系，休息很重要！|这一季先到这里，做得很好哦。
最后检查一次，就可以休息啦！|大家都完成行动了吗？那就关门吧。
辛苦啦，记得看看下一季的计划。|今天学会的技巧，要好好记住哦。
太棒了！你已经是一位可靠的公会长啦！|恭喜你，这是认真思考的回报！
没关系，每一次练习都有收获。|我们看看哪里能改进，再挑战一次吧！'''),
 'ayaka': profile('绫香','zh-TW-HsiaoYuNeural','-3%','-5Hz','清晰、专注，睿智与一闪的利落感', '''
绫香，愿与你并肩前行。|公会长，心定下来，路就会清晰。
用睿智，找出最合适的解法。|眼前的条件，总有应对之策。
把握这一瞬，随我突破！|剑光所至，便是前行之路。
先收起锋芒，静待下一季。|该进则进，该止则止。
最后的安排，也已妥当。|心无挂碍，便可收工。
本季到此，整备心神。|好好休息，下一次再展身手。
胜负已定，是你把握住了时机。|这一程，与你并肩，甚好。
收剑，复盘。还有下一次。|一时失手，不必乱了心境。'''),
 'elu': profile('艾露','zh-CN-XiaoxiaoNeural','+13%','+14Hz','敏捷、灵动，喜欢抢先行动', '''
艾露登场！可别跟丢我的脚步哦！|公会长，机会来了就要先出手！
有名气的委托，我可不会错过！|让大家都听到咱们公会的名字吧！
我先行动啦，跟上跟上！|先走一步，就能多抓住一次机会！
我先打烊，下一季可别比我慢！|今天先收手，领先也要会休息。
终于轮到我啦，关门！|最后一步，也得干脆利落！
好啦，本季任务完成！|休息一下，下一季继续抢先！
嘿嘿，抢先一步果然有效！|我们赢了！这次跑得够漂亮！
这回慢了一步，下次不会了！|别发呆，我们马上就能追上！'''),
 'melissa': profile('梅莉莎','zh-TW-HsiaoYuNeural','-6%','-10Hz','神秘、从容，好奇深渊与未知事件', '''
我是梅莉莎，未知总是令人着迷。|公会长，愿意和我看看更深处吗？
一点点积累，也会酿成奇妙的成果。|别急，下一张事件或许就有惊喜。
深渊并不只意味着危险。|去洞穴里看看吧，那里也藏着机会。
先合上书页，故事稍后继续。|我先休息，未知不会这么快消失。
最后的秘密，也记录好了。|夜深了，我们该回去了。
本季的研究，暂且告一段落。|把收获收好，明天再探索。
看吧，未知也会带来馈赠。|这段故事，终于迎来了好结局。
答案还没找到，继续研究便是。|未知仍在等待，别太早放弃。'''),
 'siren': profile('赛莲','zh-CN-XiaoyiNeural','+3%','-4Hz','理性、好奇，工坊研究员的轻快自信', '''
赛莲，实验准备完毕。|公会长，今天试试新的方案吧。
预算有限，就把设计做得更巧妙。|一份产能，也能换来新的可能。
浮空实验室，准备起航！|把研究带到迷宫里，才有新发现。
实验暂停，先整理一下数据。|我先打烊，设备也该冷却了。
最后一份数据，记录完成。|实验室关灯，今天到这里。
本季研究结束，成果已经归档。|仪器收好了，安心休息吧。
实验成功！这组结果太漂亮了。|事实证明，我们的方案可行。
失败也是数据，下次再改。|误差已经找到，我会继续优化。'''),
 'saphia': profile('莎菲亚','zh-TW-HsiaoChenNeural','+2%','-3Hz','坚定、勇敢，擅长探索和救援', '''
莎菲亚，会走在队伍最前面。|公会长，不必害怕，我来探路。
前方的迷宫，就交给我。|有人需要帮助，我就会继续前进。
再深的迷宫，也有走出去的路。|握紧希望，我们一起突破。
我先回去整备，后面就拜托了。|先收队，别让伙伴过度疲劳。
全员归来，任务结束。|最后一名也安全了，可以关门。
今天到此，照顾好受伤的伙伴。|装备收好，下次继续探路。
我们都平安回来了，这就是最好的胜利。|前路已打开，你做到了。
先保护伙伴，再考虑下一步。|只要还有人愿意前行，就有希望。'''),
 'vee': profile('薇伊','zh-CN-XiaoyiNeural','+5%','+6Hz','干练、灵巧，讲究施工与重复利用', '''
薇伊到位，图纸拿来看看。|公会长，材料备齐就能开工。
一次好设计，值得再做一遍。|把效果用足，才算没有浪费。
用手头的零件，搭出可靠的据点。|基础打牢，后面的路才稳。
我先收工，工具要保养。|今天的施工到此，别赶工伤了手。
最后一道工序，完成。|所有工具归位，关门吧。
本季施工结束，验收一下吧。|材料收好，下一季还有用。
漂亮的工程，漂亮的胜利。|我们的心血，经得起检验。
拆开看看，问题总能修好。|设计还能改，下次一定更结实。'''),
 'olivia': profile('奥莉维亚','zh-TW-HsiaoYuNeural','-8%','-12Hz','沉稳、有远见，领地经营者的笃定', '''
奥莉维亚，很荣幸与你共事。|公会长，长远的繁荣，需要耐心经营。
让产能持续增长，公会才会强大。|每一笔投入，都应当为未来铺路。
稳住领地，再向更远处拓展。|冒险者的努力，我都看在眼里。
本季先行闭店，留些余力。|我先处理领地事务，各位辛苦了。
最后的巡查结束，可以收工。|领地平安，便可安心休息。
本季经营结束，账目已经归档。|让伙伴们休息，明日再议。
繁荣来自积累，今日终于开花结果。|你的决策，为公会赢得了未来。
一次失利，不会动摇根基。|重新规划，我们仍能稳步前进。'''),
 'chris': profile('克莉丝','zh-CN-XiaoxiaoNeural','+4%','+9Hz','开朗、细心，善于安排生活与路线', '''
我是克莉丝，今天也请多关照！|公会长，把大家的日常安排好吧。
生活井然有序，收益也会跟上。|有我帮忙，日子会越来越好！
换个位置，也许就有好机会。|路线别急着定，让我再看一眼。
我先回去整理物资啦。|今天先休息，明天再一起努力。
最后一项也完成啦，关门吧！|大家都回来了，那就一起走吧。
今天的安排，圆满完成！|收拾好，我们回家啦。
太好了！大家的努力没有白费。|这份胜利，要和所有伙伴分享！
先别着急，我们重新安排一下。|这次不顺，下次会有好机会的。'''),
 'shuri': profile('舒莉','zh-TW-HsiaoChenNeural','-2%','+3Hz','聪慧、谨慎，懂交易也懂取舍', '''
舒莉，愿为你的计划出一份力。|公会长，先看看手里有哪些筹码吧。
商机藏在细节里，要仔细挑选。|专用的情报，已经替你备好了。
该付出的代价，我会算清楚。|有所取舍，才能换来更好的机会。
我先退场，留好下一季的筹码。|这一季先到这里，别贪得太多。
最后一份情报，也收好了。|该关门了，明天再谈新的交易。
本季交易结束，收获已经点清。|所有安排都妥当了，休息吧。
筹划得当，胜利自然水到渠成。|你做出了正确的取舍，恭喜。
代价比预想更高，下次重新估算。|手里的筹码还在，我们还有机会。'''),
 'macaron': profile('玛卡洛吉','zh-CN-XiaoyiNeural','+12%','+24Hz','俏皮、好奇，面对洞穴也充满兴致', '''
玛卡洛吉来啦！有什么新鲜事吗？|公会长，今天会发现什么秘密呀？
有人发现洞穴了？我也想看看！|嘿，意外的发现也有好处嘛！
瘴气散开啦，前面一定有好东西！|迷宫里的秘密，就让我找出来！
我先溜啦，明天再来玩！|今天先关门，惊喜留到下一季。
最后一位！那我也收工啦！|大家都走啦？等等我呀！
今天的发现，全都收进口袋！|打烊打烊，回去讲故事啦！
耶！我就知道会有大惊喜！|赢啦赢啦，今天真有趣！
哎呀，猜错了！下次再试！|别皱眉嘛，新的惊喜还在后面！'''),
 'sif': profile('希芙','zh-TW-HsiaoYuNeural','-5%','-7Hz','沉静、敏锐，善于借势与调度', '''
希芙，会留意每一个可用的机会。|公会长，耐心观察，再落子。
条件齐备的时候，就该行动。|不起眼的准备，也能带来回报。
让迷宫成为我们手中的筹码。|该进的地方，我会替你开路。
本季先止步，保留下一手。|我先闭店，后面的安排交给你。
最后一手，也已落定。|局面清楚了，可以收工。
本季布局结束，静待变化。|把已有的成果，稳稳留住。
时机与准备，终于汇在一起。|这一步，走得很好。
看清失误，下一步便会更稳。|局面总会变化，我们重新开始。'''),
 'frida': profile('芙莉达','zh-CN-XiaoxiaoNeural','+8%','+3Hz','洒脱、爽朗，擅长调配手牌和战力', '''
芙莉达，随时可以开工！|公会长，手牌不好就换个思路嘛。
手里总得留着几张好牌。|抓住合适的数字，生意就来了。
力量可不是白练的。|把战力准备好，回报自然会来。
我先去歇会儿，剩下的交给你们！|这一季赚够啦，先关门！
最后收个漂亮的尾！|好啦好啦，我也该收工了。
本季结束，手牌收好！|辛苦啦，下一季再大干一场。
干得漂亮！这才是咱们的水平！|哈哈，努力总算没白费！
手气不顺？下次就能转过来！|别垂头丧气，重新洗牌再来！'''),
 'bell': profile('蓓儿','zh-TW-HsiaoChenNeural','+5%','+11Hz','细致、明快，喜欢整齐的账目与收藏', '''
我是蓓儿，今天的账目就交给我吧！|公会长，整整齐齐的数字最让人安心了。
费用末位是零或五？这笔生意不错！|专用牌已经备好，等你做决定。
迷宫板块，也能带来好收益。|把收集到的成果，好好展示出来。
我先打烊，正好整理一下收藏。|账目已经对齐，今天先到这里。
最后一页也记好了，可以关门！|收尾完成，这下就整齐啦！
今天的收支，全部核对完毕！|收藏收好，下一季继续！
赢啦！账上又多了一笔漂亮的成绩！|所有努力，都变成了实实在在的回报！
这笔账先记下，下次再追回来。|没关系，整理好，我们再开始。'''),
 'horn': profile('霍伦','zh-CN-XiaoyiNeural','-1%','-1Hz','务实、沉着，注重标记组合与资源周转', '''
霍伦，资源清单已经准备好了。|公会长，让每一份积累都有用处。
凑齐合适的标记，计划就能推进。|单独的材料，也能拼成完整的收益。
资源换个用法，就有新的出路。|先积累，再把机会翻到正面。
先闭店，留好下一季的资源。|我先清点物资，各位继续。
最后一箱也清点好了。|资源归位，可以关门了。
本季周转完成，没有浪费。|把积累收好，明天继续。
资源用得其所，胜利便有了根基。|一步一步积累，我们做到了。
周转出了偏差，下次重新调配。|基础还在，我们有重新开始的余地。'''),
 'marta': profile('玛尔塔','zh-TW-HsiaoYuNeural','-12%','-2Hz','慵懒、亲切，关键时刻可靠', '''
玛尔塔在这里……有什么要紧事吗？|公会长，慢一点也没关系吧？
先把日子过好，冒险再说嘛。|能舒服地生活，也是很棒的计划。
好吧好吧，这次我认真一点。|准备好了，就一起出发吧。
我先打烊啦，午睡不能耽误。|今天够努力了，让我先休息嘛。
终于轮到我休息了……|大家都走了？那就关门吧。
辛苦啦，找个舒服的地方坐坐。|今天就到这里，晚安。
哎呀，赢了呢。偶尔认真也不错。|做得好，公会长。现在可以休息了吧？
先睡一觉，明天再想办法。|别太勉强，我们慢慢来就好。'''),
 'bell_revised': profile('贝露','zh-CN-XiaoxiaoNeural','+2%','-6Hz','自信、热心，愿意用力量换取成果', '''
贝露，已经准备好出一份力了。|公会长，需要力量的时候，就叫我吧。
有力气，就能创造新的价值。|把力量用在值得的地方。
迷宫的收获，让我来保管。|向前探索，总会有新的成果。
我先闭店，恢复一下力气。|今天已经收获不少，先休息吧。
最后的收获也带回来了。|确认完毕，可以关门了。
辛苦了，本季的努力都有收获。|把成果收好，我们下次继续。
我们的力量，终于换来了胜利！|公会长，你的信任没有白费。
还有力气，就还有下一次。|先站稳，再向前。我们不会就这样停下。'''),
}

# Short original performances tied to the printed effects, rather than long
# rules read-outs. Each print has its own three level cues.
RANKS = {
 'bai_white':'把多余情报换成金币吧。|收入更稳定了，继续按计划来。|文明向前还是向后，由你决定。',
 'bai_red':'零件到手，力量也到手。|新的力量会持续成长。|打开那块一星迷宫，看看里面有什么。',
 'hainie_white':'生活、商贸、零件，选一项节省开支吧。|收入和情报，都准备好了。|标记凑齐了，公会的积累会带来回报。',
 'hainie_red':'伙伴们的信任，会化作新的力量。|我能为大家提供更多力量了。|金币已经备好，来完成一项成就吧。',
 'misha_white':'大笔投资，可得有漂亮的回报！|收入和秘药，一起准备好！|宝物还是情报？这可真难选！',
 'misha_red':'情报和迷宫都有了，出发！|更多战力，才能走得更远！|最后的机会，也要牢牢抓住！',
 'sofia_white':'生活安稳，金币也会慢慢积累。|新的收入，会照顾好大家的日常。|把心中的计划，付诸行动吧。',
 'sofia_red':'让每一个据点，都成为可靠的归处。|守护家园的力量，正在成长。|我们的据点，会回报大家的努力。',
 'alicia_white':'商路打开了，收益自然会来。|收入提升，贸易也更顺畅了。|文明的繁荣，就是我们的财富。',
 'alicia_red':'先公开迷宫，才能做出明智的选择。|力量与零件，都准备好了。|继续行动，抓住眼前的机会！',
 'skadi_white':'必要的时候，力量也能抵作金币。|战力供给已经加强。|力量已备齐，等待下一道命令。',
 'skadi_red':'佣兵团，准备接受委托。|商业渠道已建立，委托可以继续。|再行动一次，不给机会溜走。',
 'ruby_white':'伙伴的心意，会让计划更容易实现！|收入、力量，还有新的伙伴，都来啦！|大家的支持，都化成秘药了！',
 'peria_white':'起始情报已经备好，认真选个计划吧！|收入提高啦，接下来更从容了！|整理手牌，再带上新的金币出发吧！',
 'peria_black':'第一季的生产，我会好好安排！|力量产能提高啦，继续努力！|把学到的技巧，都用在这次挑战里吧！',
 'ayaka_revised':'以睿智破局，让计划顺利施行。|准备越周全，行动越从容。|新的成就，等待我们做出选择。',
 'ayaka_red_b':'一闪之间，突破眼前险阻。|力量与一闪，均已备妥。|此刻，正是再进一步的时机。',
 'elu_reprint':'有名望的委托，我先接下啦！|收入提升，下一步更轻松！|看看新的情报，名气大的我都要！',
 'elu_red_b':'新的一季，我先出手啦！|力量、情报、零件，准备齐啦！|整理手牌，再抓住一次行动机会！',
 'melissa_white':'积累的事件，会酿成新的秘药。|收入、力量和情报，都有了新进展。|两条未知的道路，你会选择哪一条？',
 'melissa_red':'深渊洞穴，也可以成为我们的收获。|新的洞穴，等待我们去研究。|变动的迷宫，会带来什么惊喜呢？',
 'siren_white':'算好产能，这项计划就能省下不少。|收入和零件都提升了，继续研究。|让用过的能力，再发挥一次吧！',
 'siren_red':'浮空实验室，开始移动！|实验室补给完成，继续前进。|把研究成果，直接带到前线去！',
 'ruby_black':'有伙伴撤退时，我会继续向前探路。|金币、力量和伙伴，都准备好了。|把危险的未知，换成安全的道路。',
 'vee_white':'好效果，就该让它多发挥一次。|基础打得牢，工程才能走得远。|把现有的设计，继续用到实处。',
 'vee_black':'用零件省下材料，开始建造吧。|施工准备完毕，随时可以开工。|把旧的成果，转成新的力量。',
 'olivia_white':'让每一份新增产能，都带来实际收益。|经营的积累，正在稳步增长。|把眼光放远，未来才会更宽广。',
 'olivia_black':'稳步扩张，让领地为公会提供补给。|冒险者已经归队，重新安排任务吧。|准备好力量，向新的领地进发。',
 'chris_white':'生活安排妥当，收益自然会来！|大家的日常，会变得更轻松！|把生活的积累，变成前进的力量！',
 'chris_black':'换个迷宫位置，路线也许就通了！|再仔细看看地图，总有好办法！|调整好位置，再带上新的力量出发！',
 'shuri_white':'商路一通，专用情报也会送到。|把握商业的积累，继续准备。|贸易带来的成果，也能化为力量。',
 'shuri_black':'付出力量与迷宫，换来值得的事件。|好好衡量代价，再做取舍。|把有限的筹码，用在最合适的地方。',
 'macaron_white':'又有洞穴被发现啦？真有趣！|把发现收好，下次一定用得上！|背面的事件，也能重新见到阳光！',
 'macaron_black':'瘴气散开，金币也跟着来啦！|迷宫里的收获，越攒越多了！|把迷宫的星星，换成闪亮的金币！',
 'sif_white':'条件已满足，让准备换来回报。|稳住现有布局，继续等待机会。|让那张事件，再发挥一次作用。',
 'sif_black':'持有的迷宫，会为这次计划节省开支。|手中的筹码，已经更加充足。|把迷宫的价值，用在关键的一手。',
 'frida_white':'手里缺牌？先补足再说！|留好手牌，才不怕没机会！|好牌在手，下一步就好办啦！',
 'frida_black':'力量的成长，也能换来金币！|战力越扎实，收入越可靠！|让积累的力量，变成实在的回报！',
 'bell_white':'费用末位是零或五，这笔奖励别忘了！|专用牌组，还藏着新的机会！|把合适的费用，变成持续的收益！',
 'bell_black':'把迷宫放在这里，收益就到手了！|收藏还在增加，别漏记了！|有名声的板块，也会带来力量！',
 'horn_white':'每一种新标记，都值得好好积累。|把零散的资源，慢慢组织起来。|清点全部标记，收下积累的回报。',
 'horn_black':'秘药与迷宫，可以灵活周转。|资源的用法，不必拘泥一处。|那些额外的投入，到了回报的时候。',
 'marta_white':'先把领地发展好，冒险不着急。|让我再准备一会儿，就快好了。|好了，这次真的该出力了。',
 'marta_black':'简单的事件，也能让日子更宽裕。|不用太赶，慢慢积累就好。|把那张事件收回来，再用一次吧。',
 'sif_revised_white':'没有标记的事件，也有它的价值。|调整力量与收入，让布局更合适。|让事件与伙伴的积累，带来新的回报。',
 'sif_revised_black':'用迷宫换取力量，再让伙伴安全归来。|空白的区域，也能成为立足之处。|支配区域的积累，会化为新的力量。',
 'frida_revised_white':'三、六、九，这些费用可别错过！|收入和商业标记，一起到手！|看看酒馆里的冒险者，这下有回报啦！',
 'frida_revised_black':'战力成长的时候，也别忘了收金币！|调整收入，把战力供给提上去！|有了名声更高的领地，力量也更足！',
 'bell_revised_white':'把力量用起来，换成新的金币。|这份力量，也请各位一起收下。|再多行动一步，让努力继续开花。',
 'bell_revised_black':'迷宫的名声，也能带来秘药。|新的力量已经准备好，继续前进。|这次探索，让我来为你打开道路。',
 'marta_revised_white':'懒散生活，也是认真安排出来的嘛。|日子舒服了，收入也该提高一些。|伙伴们回来啦，这回该我认真冒险了。',
 'marta_revised_black':'挑一条合适的路，轻松一点去探索吧。|力量和零件准备好了，不用太着急。|把合适的领地，直接变成据点吧。',
 'horn_revised_white':'生活、商业与零件凑齐，收益就有了。|挑选合适的情报，舍去多余的负担。|把三种标记的积累，一起转成收益。',
 'horn_five_white':'三种标记成组，积累就能兑现。|情报不是越多越好，要仔细选择。|清点生活、商业与零件，收下回报吧。',
 'horn_revised_black':'先把事件背面放好，增加战力供给。|新的情报和零件，已经备妥。|把准备好的事件翻开，正式实施计划。',
}


def character_key(name):
    if name == '紫苑':
        return 'shion'
    return next(key for key, value in PROFILES.items() if value['name'] == name)


PROFILES['shion'] = profile('紫苑','zh-CN-XiaoxiaoNeural','-2%','+5Hz','温和、可靠，熟悉秘药与迷宫', '''
我是紫苑，今天也会认真帮忙。|公会长，秘药和行装都已经准备好了。
需要秘药的时候，就放心交给我吧。|合适的秘药，会让这次行动更顺利。
迷宫里的收获，我会好好保管。|让每一块迷宫，都带来实在的回报。
我先闭店，准备一下下一季的秘药。|今天先到这里，各位也请保重。
最后的伙伴也回来了，真好。|清点完毕，我们可以关门了。
本季的收获，已经整理好了。|辛苦了，来好好休息吧。
我们赢了，大家的努力都有了回报。|能陪你一起迎来胜利，我很高兴。
先照顾好自己，我们还能再试一次。|这次的经验，会帮我们走得更远。''')
RANKS['shion_white'] = '这一次的秘药格，就让我来安排。|金币产能和商业标记，都增加了。|秘药准备好了，接下来放心行动吧。'
RANKS['shion_red'] = '获得迷宫的时候，也别忘了收下金币。|力量的供给，正在稳步增加。|带上力量，再收下一块新的迷宫吧。'


def main():
    from japanese_voice_lines import LINES as JP_LINES, RANKS as JP_RANKS
    manifest = dict(schema_version=2, default_locale='ja', locales=['ja','zh_CN'], disclosure='紫苑日语使用用户录音；其他语音使用原创中日台词与Microsoft Edge在线语音合成，不模仿真人或原录音。全部语音随包离线播放。', heroes={}, clips={}, characters={})
    for key, p in PROFILES.items():
        manifest['characters'][key] = {k:v for k,v in p.items() if k != 'lines'}
        for event, lines in p['lines'].items():
            for i, text in enumerate(lines, 1):
                path = 'audio/voice/' + key + '/' + event + '-v' + str(i) + '.ogg'
                manifest['clips'][path] = dict(text=text, character=key, event=event, source='synthetic',speaker=p['speaker'],rate=p['rate'],pitch=p['pitch'])
    for hero, data in HEROES.items():
        character = character_key(data['name'])
        red = not (hero.endswith('white') or hero in ('ayaka_revised','elu_reprint'))
        variant = 'red' if red else 'white'
        events = {}
        for event in EVENTS:
            if event.startswith('select-') and event != 'select-'+variant:continue
            logical = 'intro' if event == 'intro' else 'select' if event.startswith('select-') else event
            events[logical] = ['audio/voice/'+character+'/'+event+'-v'+str(i)+'.ogg' for i in (1,2)]
        lines = RANKS[hero].split('|')
        assert len(lines) == 3
        for rank, text in enumerate(lines,1):
            path = 'audio/voice/'+character+'/'+hero+'-r'+str(rank)+'.ogg'
            events['rank_'+str(rank)] = [path]
            p = PROFILES[character]
            manifest['clips'][path] = dict(text=text,character=character,event='rank_'+str(rank),source='synthetic',speaker=p['speaker'],rate=p['rate'],pitch=p['pitch'])
        japanese = {}
        for event, paths in events.items():
            japanese[event] = []
            for index, path in enumerate(paths):
                if character == 'shion':
                    physical = 'select-intro' if event == 'intro' else 'select-'+variant if event == 'select' else event
                    if event.startswith('rank_'):physical = 'card-'+variant+'-r'+event.removeprefix('rank_')
                    else:physical += '-v'+str(index+1)
                    jp_path = 'audio/voice/kanban-010/kanban-010__'+physical+'.ogg'
                    manifest['clips'][jp_path] = dict(character=character,event=event,source='supplied_recording')
                else:
                    jp_path = path.replace('audio/voice/','audio/voice/ja/',1)
                    original = manifest['clips'][path]
                    text = JP_RANKS[hero].split('|')[int(event.removeprefix('rank_'))-1] if event.startswith('rank_') else JP_LINES[character][original['event']][index]
                    manifest['clips'][jp_path] = dict(original,text=text,speaker='ja-JP-NanamiNeural')
                japanese[event].append(jp_path)
        manifest['heroes'][hero] = dict(character=character,name=data['name'],variant=variant,events={'ja':japanese,'zh_CN':events})
    required = {path for h in manifest['heroes'].values() for language in h['events'].values() for paths in language.values() for path in paths}
    manifest['clips'] = {path:info for path,info in manifest['clips'].items() if path in required}
    overrides=ROOT/'docs/SUPPLIED_VOICE_OVERRIDES.json'
    if overrides.is_file():
        supplied=json.loads(overrides.read_text('utf8'))
        for path,info in supplied['clips'].items():
            if path not in manifest['clips']:raise RuntimeError('Supplied recording does not match a current cue: '+path)
            manifest['clips'][path]=info
        manifest['disclosure']='日语优先使用用户提供的13组录音；缺失片段与中文保留已有角色合成配音。全部语音随包离线播放。'
        manifest['supplied_archive_sha256']=supplied['archive_sha256']
    target = SRC/'data/voice_manifest.json'
    target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n','utf8')
    docs = ROOT/'docs/CHARACTER_VOICES.json'
    docs.write_text(json.dumps(dict(characters=manifest['characters'],heroes=manifest['heroes'],clips=manifest['clips'],disclosure=manifest['disclosure']),ensure_ascii=False,indent=2)+'\n','utf8')
    print(json.dumps(dict(characters=len(manifest['characters']),hero_versions=len(manifest['heroes']),unique_clips=len(manifest['clips']),synthetic=sum(c['source']=='synthetic' for c in manifest['clips'].values()),supplied=sum(c['source']=='supplied_recording' for c in manifest['clips'].values())),ensure_ascii=False))


if __name__ == '__main__':
    main()
