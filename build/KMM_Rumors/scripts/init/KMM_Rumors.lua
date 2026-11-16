-- KMM_Rumors v0 — слухи из хроники дирижёра (поток B RUMORS).
-- Источник: C:\KenshiModMap\logs\chronicle.log (контракт потока A, TSV):
--   game_day, event_id, event_type, town_sid, town_name, faction_attacker, faction_defender,
--   leader_sid, leader_name, status, text
-- Доставка (то, что подтверждено рабочими примерами CK/Bloodlines или биндингами — см. docs/streams/RUMORS.md):
--   * реплика NPC рядом с игроком: Character:say(text)              [подтверждено: CKBloodlines.lua]
--   * журнал услышанного (V3):     ManagementScreen.getSingleton():addMessage(owner, msg, ML_NORMAL)   [✓код BindingsReference ManagementScreen; в игре — маркер «journal: addMessage ok»]
--   * мелочь города при входе (V4), чистые имена и слияние шума (V6), глобальная память рассказанного (V2), метрика VISIBILITY (B1)
-- Задержка: слух доступен через расстояние(событие, игрок)/NEWS_SPEED дней (0..NEWS_MAX_DAYS), крупные события быстрее, вестники (беженцы/караван рядом) — сразу.
-- Искажение: зависит от роли рассказчика (имя шаблона персонажа) и расстояния до места события.

----------------------------------------------------------------------- ПАРАМЕТРЫ
local CFG = {
  CHRONICLE_PATH       = "C:/KenshiModMap/logs/chronicle.log",
  TOLD_PATH            = "C:/KenshiModMap/logs/rumors_told.tsv",  -- только журнал для диагностики; рабочий список — в сейве (kmm_rumors_told)
  LOG_PATH             = "C:/KenshiModMap/logs/rumors.log",       -- наш лог доставки (для проверки)
  LANG                 = "en",     -- "en" | "ru" (кириллица в пузыре реплики не проверена — игра на en_GB)
  -- НОВОСТИ С ЗАДЕРЖКОЙ (2026-11-13): слух доступен через dist/NEWS_SPEED дней после события (0..NEWS_MAX_DAYS).
  -- Калибровка: карта ~ +-140k ед., медиана расстояния до ближайшего города ~11k -> сосед ~0.6 дня, через полкарты ~4 дня, край-в-край 7 (предел).
  NEWS_SPEED           = 18000,    -- единиц мира в игровой день (новость идёт со скоростью путника)
  NEWS_MAX_DAYS        = 7,        -- потолок задержки
  NEWS_NOCOORD_DAYS    = 1,        -- события без координат (руда, сюжет): общая задержка
  BIG_SPEED_MULT       = { faction_fell = 4, town_captured = 3, faction_split = 2, leader_killed = 2, succession_crisis = 2, chaos_incursion = 3, faction_rise = 1.5 },  -- крупные события идут быстрее
  HERALD_RADIUS        = 4000,     -- путник (беженцы/караван из Traces.travelers) ближе стольких ед. к игроку = вестник
  HERALD_NEWS_RADIUS   = 45000,    -- вестник приносит вести о событиях не дальше стольких ед. от места, откуда он идёт
  MAX_AGE_DAYS         = 90,       -- старше — уже не новость
  FAR_DISTANCE         = 150000,   -- дальше — искажение +1 уровень
  CHECK_INTERVAL_SEC   = 20,       -- как часто (реальные секунды) проверять, есть ли кому рассказать
  TALK_RADIUS          = 900,      -- рассказчик должен быть ближе стольких единиц к персонажу игрока
  -- B1/V2 пропускная способность: окно города TOWN_COOLDOWN_HOURS игровых часов, в нём до MAX_PER_TOWN слухов,
  -- между слухами не меньше RUMOR_GAP_SEC реальных секунд (пузыри не налезают друг на друга)
  TOWN_COOLDOWN_HOURS  = 8,
  MAX_PER_TOWN         = 3,
  RUMOR_GAP_SEC        = 40,
  MAX_PER_CHECK        = 1,        -- слухов за одну проверку
  SPEAKER_MAX_DAY      = 2,        -- один рассказчик — не больше стольких слухов за игровой день; повторный рассказчик в визите — штраф
  -- приоритет кандидата: вес типа x свежесть x близость (близость к игроку/городу), тай-брейк — расстояние, потом свежесть
  FRESH_DAYS           = 2,        -- свежесть = 1/(1 + возраст/FRESH_DAYS)
  NEAR_SCALE           = 20000,    -- близость = 1/(1 + расстояние/NEAR_SCALE); без координат — 0.5
  BIG_WEIGHT           = 3,        -- вес крупных событий (тип есть в BIG_SPEED_MULT)
  HERALD_WEIGHT        = 1.5,      -- весть принёс путник
  -- V6 шум: однотипные события одной пары за MERGE_DAYS сливаются в один слух (остальные помечаются рассказанными),
  -- суточный потолок рассказанного и пониженный вес; дело самого игрока (by_player) потолком не режется
  MERGE_DAYS           = 1,
  NOISY                = { deed = { cap = 2, weight = 0.35 }, loot_carried = { cap = 1, weight = 0.25 },
                           nemesis_contempt = { cap = 1, weight = 0.8 }, nemesis_beat_again = { cap = 1, weight = 0.8 } },   -- соперник и игрок: не чаще слуха в сутки на вид
  -- V3 журнал услышанного: каждый сказанный слух — строка во вкладке сообщений (ManagementScreen:addMessage, ML_NORMAL)
  JOURNAL_ON           = true,
  JOURNAL_MAX_DAY      = 15,       -- строк за игровой день
  JOURNAL_MAX_CHARS    = 200,
  JOURNAL_QUEUE        = 6,        -- окна ещё нет (ранняя загрузка) — строки ждут
  SHOW_IN_MESSAGE_LOG  = false,    -- фолбэк, если класса ManagementScreen нет: GameWorld:showPlayerAMessage_withLog
  -- V4 город всегда говорит при входе: в визите не прозвучал слух — через ENTRY_DELAY_SEC местная мелочь из модели
  SMALLTALK_ON         = true,
  ENTRY_DELAY_SEC      = 45,       -- после приветствия Nemesis (greet_delay_s 25)
  SMALLTALK_CD_HOURS   = 6,        -- не чаще раза на город
  NEAR_OUTLAW_R        = 25000,    -- разыскиваемый ближе к игроку — «бродит рядом»
  NEAR_TRAVELER_R      = 15000,
  STOCK_LOW            = 0.5,      -- полка KMM_Stock ниже доли нормы — «дорого»
  STOCK_HIGH           = 1.4,      -- выше — «дёшево»
  VIS_LOG_SEC          = 300,
  -- ревью: память рассказанного в сейве не растёт годами — раз в игровой день и при сохранении удаляются записи о событиях,
  -- которых нет в журнале дирижёра или которые старше TOLD_KEEP_DAYS, и самые старые сверх TOLD_MAX (только при источнике-дирижёре)
  TOLD_KEEP_DAYS       = 120,      -- > MAX_AGE_DAYS: такие события слухом уже не станут
  TOLD_MAX             = 3000,     -- ключей told + heard      -- B1 метрика: строка VISIBILITY в rumors.log не чаще (и при сохранении)
  WRONG_OUTCOME_CHANCE = 0.3,      -- уровень искажения 2: шанс перепутать исход (убит <-> пленён / отбились <-> пал)
  -- роль рассказчика по имени шаблона (data.name), первое совпадение; уровень: 0 точно, 1 без имён, 2 преувеличивает/путает
  ROLES = {
    { match = { "barman", "bartender", "bar keeper", "innkeeper" }, level = 0, prefer = 3, kind = "barman" },
    { match = { "trader", "merchant", "caravan", "shop" },           level = 0, prefer = 2, kind = "trader" },
    { match = { "guard", "samurai", "soldier", "police", "paladin" }, level = 1, prefer = 1, kind = "guard" },
    { match = { "bandit", "thug", "drifter", "vagrant", "beggar", "slave" }, level = 2, prefer = 1, kind = "low" },
  },
  DEFAULT_LEVEL        = 1,
  -- B1 формы речи: вес формы по манере рассказчика (номер формы: 1 прямо, 2 слух, 3 коротко/грубо, 4 с оценкой; 5+ как 2)
  MANNER = { barman = { 1, 3, 1, 3 }, trader = { 3, 1, 1, 3 }, guard = { 3, 1, 3, 1 }, low = { 1, 2, 3, 1 }, default = { 2, 3, 2, 1 } },
  -- одна форма (ключ «тип#номер») — не чаще раза в FORM_YEAR_DAYS игровых дней; учёт в сейве (kmm_rumors_forms), потолок FORMS_MAX
  FORM_YEAR_DAYS       = 365,
  FORMS_MAX            = 2000,
}

local TAG = "[KMM_Rumors] "

----------------------------------------------------------------------- ТЕКСТЫ
local T = {
  en = {
    -- B1 формы речи (en): [1] прямо, [2] слух через третьих, [3] коротко и грубо, [4] с оценкой рассказчика, [5+] ещё слух.
    -- Ключ формы «тип#номер»: одна форма — не чаще раза в FORM_YEAR_DAYS (CFG); все формы типа за год сказаны — слух этого типа молчит
    leader_killed = { "%LEADER% is dead. %ATT% killed him at %TOWN%.", "Word is %LEADER% was cut down at %TOWN%. %ATT% did it, they say.", "%LEADER%? Dead. %ATT% saw to it at %TOWN%.", "%ATT% killed %LEADER% at %TOWN%. Bold. Or stupid. We'll see which." },
    leader_captured = { "%ATT% took %LEADER% alive at %TOWN%.", "Heard %LEADER% is wearing %ATT% chains now. Taken at %TOWN%, they say.", "%LEADER% is in a cage. %ATT% have him.", "%ATT% caught %LEADER% at %TOWN%. Alive is worse than dead, if you ask me." },
    attack_repelled = { "%ATT% hit %TOWN% and %DEF% threw them back.", "They say %ATT% went for %TOWN%, but %DEF% held the walls.", "%ATT% tried %TOWN%. Got their teeth kicked in by %DEF%.", "%DEF% held %TOWN% against %ATT%. Good for them. Won't be the last try, though." },
    raid = { "%ATT% raided %DEF%. Carts of loot went past here.", "Heard %DEF% got hit by %ATT% again.", "%ATT% robbed %DEF% blind. Same old.", "%ATT% keep raiding %DEF%. Someone ought to stop them, but nobody will.", "Folk say %ATT% bands came down on %DEF% in the night." },
    town_captured = { "%TOWN% belongs to %ATT% now. %DEF% lost it.", "They say %ATT% flew their colours over %TOWN%.", "%TOWN% fell. %ATT% own it now.", "%ATT% took %TOWN% off %DEF%. New masters, same taxes, I'd wager." },
    mobilized = { "%ATT% are on the march. Big warbands, out in the open.", "Word is something stirred %ATT%. They're mustering.", "%ATT% are arming up. Stay off the roads.", "When %ATT% march like that, somebody's town burns. Hope it isn't ours." },
    demobilized = { "%ATT% went back to their own business.", "Folk say whatever riled %ATT% is over.", "%ATT% stood down. For now.", "%ATT% quieted down. I don't trust it." },
    treaty_signed = { "%ATT% and %DEF% made a deal.", "Word is %ATT% and %DEF% shook hands.", "%ATT% and %DEF%, friends now. Huh.", "%ATT% and %DEF% signed something. Deals like that cost someone else." },
    treaty_broken = { "%ATT% and %DEF% are done with each other.", "Heard that pact between %ATT% and %DEF% is gone.", "%ATT% tore up the deal with %DEF%.", "%ATT% and %DEF% broke it off. Never lasts, does it?" },
    betrayal = { "%ATT% stabbed %DEF% in the back.", "They say %DEF% trusted %ATT%, and paid for it.", "%ATT% sold out %DEF%. Snakes.", "%ATT% betrayed %DEF%. Nobody sane will deal with them now." },
    ally_help = { "%ATT% came to help %DEF%. Kept their word.", "Word is %ATT% sent fighters to back %DEF%.", "%ATT% showed up for %DEF%. Fair play.", "%ATT% stood by %DEF%. Rare thing these days." },
    ally_failed = { "%DEF% called for help and %ATT% never came.", "Heard %ATT% left %DEF% to hang.", "%ATT% let %DEF% down. Cowards.", "%ATT% broke faith with %DEF%. Remember that before you trust them." },
    faction_fell = { "%ATT% are finished. Scattered to the winds.", "They say nobody's seen %ATT% in a while. Done for.", "%ATT%? Gone. Dead or run off.", "%ATT% are no more. The world won't miss them much." },
    faction_rise = { "%ATT% are getting strong. More towns every season.", "Word is %ATT% are taking ground everywhere.", "%ATT% are on the up. Get used to it.", "Mark my words, %ATT% will rule half the map." },
    faction_decline = { "%ATT% are losing ground.", "Folk say things look bad for %ATT%. Town after town lost.", "%ATT% are slipping.", "%ATT% are on the way down. Wouldn't want to be one of them." },
    revolt = { "%TOWN% rose up against %DEF%.", "Heard the people of %TOWN% threw %DEF% out.", "%TOWN% kicked out %DEF%. Just like that.", "%TOWN% turned on %DEF%. Squeeze people long enough and they bite." },
    town_rejoined = { "%TOWN% went back to %ATT%. No fighting.", "They say %ATT% have %TOWN% again. Quietly.", "%TOWN% is %ATT% again.", "%TOWN% is back with %ATT%. Better the devil you know." },
    mine_exhausted = { "The seams at %TOWN% are dead. The miners walked off.", "Word is there's nothing left to dig at %TOWN%.", "%TOWN% mine's empty.", "The %TOWN% mine is played out. Hard times for that lot." },
    mine_opened = { "%ATT% sank a deep mine at %TOWN%.", "Heard %ATT% are digging deep near %TOWN%.", "%ATT% got a new mine at %TOWN%.", "%ATT% are digging at %TOWN%. Iron's worth the risk now, I suppose." },
    ore_crisis = { "Iron is scarce everywhere. Smiths melt down old blades.", "They say every caravan with ore gets hit these days.", "No iron. Anywhere.", "Metal prices keep climbing. People will kill for scrap soon, mark my words." },
    ore_claim = { "%ATT% say the Nameless dig their iron near %TOWN%. They want their cut.", "Word is %ATT% are counting the ore the Nameless haul out near %TOWN%.", "%ATT% want a cut of the Nameless iron at %TOWN%.", "The Nameless dig near %TOWN% and %ATT% want their share. That ends with a tax man or a sword." },
    story_scramble = { "More and more people are digging in the old ruins.", "They say something is out there in the ruins. Everyone's digging.", "Ruin-diggers everywhere. Fools with shovels.", "Every fool with a shovel thinks he'll get rich in the ruins. Most just get dead." },
    story_famine = { "Iron is the only thing anyone talks about now.", "Word is smiths are turning customers away. No metal.", "No metal. No work.", "Hunger for metal is worse than hunger for bread, some say. I'm not so sure." },
    story_twilight = { "The old war-gear is failing.", "They say ancient armour cracks and nobody can mend it.", "Old gear's breaking. Good riddance.", "The ones who wore the old armour are nervous. As they should be." },
    story_night = { "The dark gods whisper louder every month.", "Folk say even the guards pray at night now.", "Bad nights. Bar your door.", "People pray to anything that listens these days. Can't blame them." },
    story_forge = { "Smiths say the ancient craft can be learned again.", "Word is some forge is making old-style steel again.", "Good steel's coming back. Costly.", "The old craft is coming back, slowly. About time something did." },
    story_ashes = { "Too many burned towns. Folk are starting over in the ashes.", "They say the worst of it has passed. What's left is ash.", "Ash and graves. That's what's left.", "Stubborn people are rebuilding on the ashes. I respect that." },
    story_quiet = { "Fires burn quietly again. The worst is behind us.", "Folk say the roads are calm these days.", "Quiet times. Enjoy them.", "The worst is behind us, they say. For now. It never lasts." },
    elite_hunger = { "%ATT% can't mend their wonders anymore.", "Heard even %ATT% are running out of the old parts.", "%ATT% are scraping for parts.", "%ATT% patrols look desperate. Desperate men are dangerous." },
    ruin_expedition = { "%ATT% went digging in %TOWN%. Came back with scrap.", "Word is %ATT% hauled junk out of %TOWN%.", "%ATT% looted the ruins at %TOWN%.", "%ATT% are picking %TOWN% clean. Let's hope they don't wake anything." },
    famine = { "Hunger in %TOWN%. Families on the roads.", "They say %ATT% can't feed their people. Bread lines at %TOWN%.", "%TOWN% is starving.", "%TOWN% is going hungry and %ATT% do nothing. Shameful." },
    theft = { "Thieves of %ATT% cleaned out %DEF% storehouses.", "Word is the stolen goods everywhere are %ATT% work.", "%ATT% robbed %DEF% stores.", "%ATT% thieves hit %DEF% again. Lock up your goods." },
    drug_bust = { "%ATT% caught smugglers of %DEF% with a load of hash.", "Heard %ATT% burned a hashish cargo of %DEF%.", "%ATT% busted %DEF% smugglers.", "%ATT% burned %DEF% hash. Prices will go up, you watch." },
    slave_raid = { "%ATT% hunters took people of %DEF% in chains.", "They say another slave column came from %DEF% lands. %ATT% again.", "%ATT% grabbed %DEF% folk. Chains and all.", "%ATT% are taking %DEF% people as slaves. Filthy business." },
    black_market = { "%ATT% unloaded a cargo at %TOWN% you don't ask about. %DEF% paid.", "Word is %DEF% buy from %ATT% at %TOWN%. Everyone knows, nobody says.", "%ATT% sell, %DEF% buy, at %TOWN%. Don't ask what.", "Busy nights at %TOWN%: %ATT% and %DEF% trading things best left unnamed. Not my business." },
    slaves_freed = { "%ATT% struck a %DEF% slave column and set them all free.", "Heard %ATT% freed slaves of %DEF%.", "%ATT% broke %DEF% chains.", "%ATT% freed %DEF% slaves. Good. Some things need doing." },
    succession_crisis = { "%ATT% are fighting over who leads them.", "They say nobody rules %ATT% now. Knives are out.", "%ATT% have no boss. Chaos.", "%ATT% are tearing themselves apart over the top seat. Fools." },
    succession_resolved = { "%ATT% have a new master.", "Word is the squabbling in %ATT% is over.", "%ATT% got a new boss.", "%ATT% settled on a new leader. Let's see if this one lasts." },
    faction_split = { "%ATT% broke away from %DEF%.", "Heard %DEF% split. %ATT% walk their own road now.", "%ATT% left %DEF%. Clean break.", "%ATT% went their own way from %DEF%. Trouble will follow." },
    warlord_rose = { "A warlord gathers men. %ATT%, they call themselves.", "They say some warlord is rallying the angry ones of %DEF%. %ATT%.", "New warband out there: %ATT%.", "%ATT% are a warlord's crew. Men like that end badly, and take others with them." },
    chaos_cult = { "Strange cultists in %TOWN%. Whispering about dark gods.", "Word is people vanish at night in %TOWN%.", "Cultists in %TOWN%. Stay away.", "Something foul grows in %TOWN%. I wouldn't sleep there." },
    base_raid = { "%ATT% want what's in that new settlement of the Nameless.", "Heard %ATT% plan to hit the Nameless settlement.", "%ATT% are coming for the Nameless.", "%ATT% keep talking about the Nameless and their settlement. Won't end well for someone." },
    recruit_merc_hired = { "%LEADER% of %ATT% hired %DEF% blades near %TOWN%.", "They say %ATT% paid %DEF% to guard %LEADER%. Two days.", "%LEADER% has %DEF% guards now.", "%LEADER% hired %DEF% swords. Strike when the contract runs out, if you're clever." },
    recruit_merc_left = { "The %DEF% blades left %LEADER% of %ATT%. Contract's over.", "Word is %LEADER% of %ATT% walks without guards again.", "%LEADER%'s guards went home.", "%LEADER% of %ATT% is on his own again. Careless." },
    recruit_slave_bought = { "%ATT% bought the strongest slave in %TOWN%: %LEADER%.", "Heard %ATT% took %LEADER% from the %TOWN% cages first.", "%LEADER% went to %ATT%. Sold.", "%ATT% snapped up %LEADER% in %TOWN%. Nobody else had a chance." },
    recruit_slave_freed = { "%LEADER%, bought by %ATT%, walks free.", "They say somebody broke %LEADER% out of %ATT% chains.", "%LEADER% got loose from %ATT%.", "%LEADER% slipped the %ATT% chains. Good for him." },
    ally_joins = { "%ATT% marched out against %DEF%, beside some drifters.", "Word is %ATT% joined a fight against %DEF%.", "%ATT% went after %DEF%.", "%ATT% took on %DEF% with the Nameless at their side. Strange company." },
    relic_salvage = { "%ATT% dragged something ancient out of the ruins.", "They say %ATT% found a vault of the old ones.", "%ATT% got an old-world relic.", "%ATT% found something that still hums. I'd leave it buried." },
    elite_seen = { "%ATT% sent their elite out near %TOWN%.", "Heard an honour guard of %ATT% was seen by %TOWN%.", "%ATT% elite near %TOWN%. Steer clear.", "%ATT% heavy armour near %TOWN%. Cold eyes. Nothing good comes of that." },
    stock_shortage = { "%TOWN% is running out of %CAT%.", "Word is you can't find %CAT% in %TOWN% for love or money.", "No %CAT% in %TOWN%.", "%CAT% is short in %TOWN%. Prices will climb, you'll see." },
    stock_glut = { "%TOWN% is drowning in %CAT%.", "They say traders sell %CAT% for nothing in %TOWN%.", "Cheap %CAT% in %TOWN%.", "Too much %CAT% in %TOWN%. Good time to buy, if you're smart." },
    stock_sacked = { "%ATT% stripped %TOWN% bare.", "Heard the warehouses of %TOWN% were looted by %ATT%.", "%ATT% emptied %TOWN%.", "%ATT% sacked %TOWN%. Those poor traders." },
    town_shortage = { "Workshops in %TOWN% are short on %CAT%.", "Word is the smiths of %TOWN% stand idle. No %CAT%.", "%TOWN% is out of %CAT%.", "No %CAT% in the workshops of %TOWN%. Idle hands, empty bellies." },
    smuggle_run = { "Smugglers got a load of %CAT% into %TOWN% past the guards.", "They say somebody ran %CAT% into %TOWN% in the night.", "Smuggled %CAT% in %TOWN%. Don't ask.", "Smugglers brought %CAT% to %TOWN%. Pricey, but at least it's there." },
    contraband_caught = { "%ATT% guards nabbed a drifter selling %CAT% in %TOWN%.", "Heard a Nameless trader was caught peddling %CAT% in %TOWN%.", "Somebody got caught with %CAT% in %TOWN%. %ATT% are furious.", "Selling %CAT% under %ATT% noses in %TOWN%. Brave or stupid." },
    gear_worn = { "%ATT% patrols walk about in rusted armour.", "Word is %ATT% armouries are empty.", "%ATT% soldiers in rust and rags.", "%ATT% kit is falling apart. Hard times for them, easier for their enemies." },
    player_sold = { "Some drifter has been selling %CAT% in %TOWN%. Prices are falling.", "They say a Nameless trader unloaded a lot of %CAT% in %TOWN%.", "Cheap %CAT% in %TOWN%. Some drifter dumped it.", "A drifter is flooding %TOWN% with %CAT%. The local traders hate it." },
    caravan_lost = { "A %ATT% caravan never arrived.", "Heard %ATT% lost a trade caravan on the road. Bodies by the track.", "%ATT% caravan's gone. Wolves or bandits.", "Another %ATT% caravan lost. The roads get worse every season." },
    refugees = { "Refugees from %TOWN% are on the roads.", "Word is whole families left %TOWN% with what they could carry.", "%TOWN% folk on the run. Hungry ones.", "Refugees from %TOWN% everywhere. Poor souls, and nobody wants them." },
    relic_forge_known = { "The Nameless built a thinking machine of the ancients.", "They say some drifters assembled a machine mind.", "Drifters made a machine that thinks. Madness.", "A machine mind, built by drifters. Fools or geniuses, I can't decide." },
    trade_for = { "%ATT% are buying up %CAT% from %DEF%.", "Heard caravans of %ATT% carry %CAT% from %DEF%. Paid in full.", "%ATT% want %CAT%. %DEF% sell.", "%ATT% pay %DEF% any price for %CAT%. Somebody's getting rich." },
    raid_surplus = { "%ATT% came back from %TOWN% loaded with %CAT%.", "Word is %ATT% have more %CAT% than they can store after %TOWN%.", "%ATT% robbed %TOWN%. Swimming in %CAT% now.", "%ATT% sit on piles of %CAT% from %TOWN%. Stolen goods sell cheap." },
    waylay = { "%ATT% are robbing travellers of %DEF% on the roads.", "They say %ATT% wait in the hills for %DEF% caravans.", "%ATT% on the roads. Take an escort.", "%ATT% keep picking off %DEF% caravans. Nobody's safe out there." },
    loot_sold = { "Somebody is selling plundered %CAT% in %TOWN%.", "Heard %ATT% unload their loot in %TOWN%. Mostly %CAT%.", "Stolen %CAT% in %TOWN%. Cheap.", "%ATT% loot on the %TOWN% market. Buy it and you're no better than them." },
    chaos_incursion = { "Something tore the sky open near %TOWN%. Things with horns came out.", "They say daemons walk near %TOWN%.", "Daemons near %TOWN%. I'm not joking.", "Horned things near %TOWN%. End of the world, some say. I'd believe it." },
    nemesis_contempt = { "%LEADER% caught the Nameless with empty pockets and let them crawl off.", "They say %LEADER% spat at the Nameless and walked away. Not worth robbing.", "%LEADER% didn't even bother with the Nameless. Too poor.", "%LEADER% let the Nameless go, broke and beaten. That's a grudge in the making." },
    nemesis_beat_again = { "%LEADER% put the Nameless in the dirt again.", "Heard %LEADER% beat the Nameless once more. %ATT% drink to it.", "%LEADER% beat the Nameless. Again.", "%LEADER% keeps beating the Nameless. One day it'll go the other way." },
    trade_route = { "%ATT% caravans run to %TOWN% now.", "Word is %ATT% and %DEF% are doing business at %TOWN%.", "New road to %TOWN%. %ATT% trade there.", "%ATT% caravans to %TOWN%, steady trade with %DEF%. Good for everyone, for once." },
    loot_carried = { "A band of %ATT% went by, hauling loot from a fight.", "They say %ATT% are dragging plunder off a battlefield to the markets.", "%ATT% with loot. Keep away.", "%ATT% hauling plunder again. Somebody lost that fight badly." },
    base_campaign = { "%ATT% want what's in that new settlement of the Nameless.", "Heard %ATT% plan to hit the Nameless settlement.", "%ATT% are coming for the Nameless.", "%ATT% keep talking about the Nameless and their settlement. Won't end well for someone." },
    -- формы для типов без шаблона (готовый текст события %TEXT%): та же манера по номеру
    wrap = { "%TEXT%", "Word on the road: %TEXT%", "%TEXT% That's all I know.", "%TEXT% Mark my words, there's more to it." },
    -- story_* (выше): сюжет идёт оборотами (~5 лет), каждый может звучать снова — тексты без «впервые/навсегда»; номер оборота (cycle) не выводится
    cats = { food = "food", metal = "metal", weapons = "weapons", armor = "armour", med = "medicine", drugs = "drugs", lux = "luxuries", scrap = "scrap", goods = "goods" },
    some_leader = "some big shot", some_faction = "someone", far = "somewhere far to the %DIR%",
    dirs = { n = "north", s = "south", e = "east", w = "west" },
    hedge = { " Or so they say.", " Don't quote me.", "" },
    herald = "Newcomers off the road say: ",
    msg = "Rumour (%WHO%): %TEXT%",
    merged = " And not for the first time, either.",
    place_dir = "a place to the %DIR%", place_any = "somewhere out in the wastes",
    journal_owner = "Rumour", journal_day = "Day %d, %s: %s", journal_day0 = "Day %d: %s",
    small = {
      owner = { "%OWNER% run this town. Their law, their prices.", "This is %OWNER% ground. Keep your nose clean." },
      low   = { "%CAT% is dear here this week. The stalls are near empty.", "Good luck finding %CAT% in this town. Everyone is short." },
      high  = { "Plenty of %CAT% in the stalls. Cheap, for once.", "Traders here are sitting on piles of %CAT%." },
      outlaw = { "There is a price on %NAME%, %BOUNTY% cats. Seen around these parts.", "%NAME% was spotted not far from here. %BOUNTY% cats on that head." },
      refugees = { "Refugees came through on the road. Hungry and quiet." },
      caravan = { "A caravan passed by not long ago. Guards looked nervous." },
      column = { "A column of %FAC% marched past. In a hurry, too." },
      courier = { "A %FAC% runner went by at full tilt. Something is up." },
      traveler = { "Drifters on the road again. More every week." },
      quiet = { "Quiet week. Caravans come, caravans go.", "Nothing much happens here. That is how we like it.", "Same dust, same faces. Buy something or move on." },
      -- бытовая болтовня (B1): без годового учёта форм, может повторяться; вес — по состоянию города (smallLines)
      weather = { "Hot again. The wind just moves the dust around.", "Dust storm coming, by the look of the sky.", "Cold night last night. Couldn't sleep.",
                  "Rain? Haven't seen rain in years." },
      work = { "Long day at the workshop. My back is killing me.", "Pay's late again. Always late.", "Somebody has to haul the crates. Today it was me.",
               "The mines want more hands. Not mine, thanks." },
      guard = { "Guards are on edge today. Keep your hands where they can see them.", "Watch for pickpockets near the bar.",
                "The patrol came through twice this morning. Twice." },
      tense = { "Somebody threw a rock at the guards last night. It'll get worse.", "People whisper in corners. Nobody trusts anybody.",
                "The guards beat a man in the street today. Folk just watched." },
      hunger = { "Bread is thin and dear. My kids ate twice this week.", "Saw a man fight a dog for scraps today.", "Everyone's counting rations. Nobody says it out loud." },
      prices = { "Prices went up again. Everything costs double.", "Traders smile and charge you twice. Same as ever.", "Can't afford a decent meal on my pay." },
    },
  },
  ru = {
    leader_killed   = { "Говорят, %LEADER% убит у %TOWN%. Это всё %ATT%.", "Слыхал? %LEADER% мёртв — %ATT% ударили по %TOWN%." },
    leader_captured = { "Говорят, %ATT% взяли %LEADER% живым у %TOWN%.", "Ходят слухи, %LEADER% теперь в цепях у %ATT%." },
    attack_repelled = { "%ATT% полезли на %TOWN%, но %DEF% отбились.", "У %TOWN% была драка. %DEF% выстояли." },
    raid            = { "%ATT% ограбили %DEF% — мимо везли добычу.", "Слыхал, %DEF% опять пострадали от %ATT%." },
    town_captured   = { "%TOWN% теперь за %ATT%. %DEF% её потеряли.", "Говорят, над %TOWN% теперь знамёна %ATT%." },
    mobilized       = { "%ATT% выступили. Большие отряды, открыто.", "Что-то растревожило %ATT%. Собирают силы." },
    demobilized     = { "%ATT% снова затихли.", "Похоже, %ATT% успокоились." },
    treaty_signed   = { "%ATT% и %DEF% договорились.", "Говорят, %ATT% и %DEF% ударили по рукам. Жди беды." },
    treaty_broken   = { "%ATT% и %DEF% разошлись.", "Того уговора между %ATT% и %DEF% больше нет." },
    betrayal        = { "%ATT% предали %DEF%. Им теперь никто не поверит.", "%DEF% доверились %ATT%. Зря." },
    ally_help       = { "%ATT% пришли на помощь %DEF%. Слово сдержали.", "%ATT% прислали бойцов за %DEF%." },
    ally_failed     = { "%DEF% звали на помощь, а %ATT% не пришли.", "%ATT% бросили %DEF% одних." },
    faction_fell    = { "С %ATT% покончено. Разбежались кто куда.", "Про %ATT% давно не слышно. Конец им." },
    faction_rise    = { "%ATT% набирают силу. Что ни сезон — новый город.", "Попомни моё слово, %ATT% полмира под себя подомнут." },
    faction_decline = { "%ATT% сдают позиции.", "Плохи дела у %ATT%: город за городом теряют." },
    revolt          = { "%TOWN% восстала против %DEF%.", "Слыхал, в %TOWN% прогнали %DEF%." },
    town_rejoined   = { "%TOWN% вернулась к %ATT%. Тихо, без драки.", "%ATT% снова держат %TOWN%." },
    mine_exhausted  = { "Жилы у %TOWN% выработаны. Шахтёры просто ушли.", "У %TOWN% копать больше нечего." },
    mine_opened     = { "%ATT% пробили глубокую шахту у %TOWN%. Железо того стоит.", "%ATT% роют глубоко у %TOWN%." },
    ore_crisis      = { "Железа нигде нет. Кузнецы перековывают старые клинки.", "Металл дорожает. Любой караван с рудой грабят." },
    story_scramble  = { "В старых руинах копаются всё чаще. Говорят, там что-то есть.", "Копатели руин опять за своё. Каждый дурак с лопатой мечтает разбогатеть." },
    story_famine    = { "Теперь все говорят только о железе. Голод по металлу.", "Металла опять не достать. Кузнецы гонят заказчиков." },
    story_twilight  = { "Древнее снаряжение отказывает. Те, кто его носил, нервничают.", "Древняя броня трескается, и чинить некому. Гордецы боятся." },
    story_night     = { "Тёмные боги шепчут всё громче. Даже стража молится.", "Опять дурные ночи. Люди запирают двери и молятся кому угодно." },
    story_forge     = { "Кузнецы говорят: древнему ремеслу можно научиться заново. Медленно и дорого.", "Где-то опять куют сталь по-старому. Дорого, зато настоящая." },
    story_ashes     = { "Слишком много сожжённых городов, слишком много могил. Люди разбирают пепелища и начинают заново.", "Худшее, говорят, позади. Остались пепел да упрямые люди." },
    story_quiet     = { "У костров снова тихо. Говорят, худшее позади. Пока что.", "На дорогах спокойно, в барах людно. Тихие времена, пока длятся." },
    elite_hunger    = { "%ATT% больше не могут чинить свои диковины. Патрули злые и голодные.", "Даже у %ATT% кончаются старые детали." },
    ruin_expedition = { "%ATT% полезли в %TOWN%. Вернулись со скрапом.", "Видел, как %ATT% тащили хлам из %TOWN%." },
    famine          = { "В %TOWN% голод. Семьи уходят по дорогам.", "%ATT% не могут прокормить своих. Очереди за хлебом в %TOWN%." },
    theft           = { "Воры %ATT% обчистили склады %DEF%.", "Краденое повсюду — работа %ATT%, говорят." },
    drug_bust       = { "%ATT% поймали контрабандистов %DEF% с гашишем.", "%ATT% сожгли груз гашиша. %DEF% это не понравится." },
    slave_raid      = { "Охотники %ATT% увели людей %DEF% в цепях.", "Опять колонна рабов с земель %DEF%. Снова %ATT%." },
    black_market    = { "%ATT% сбыли в %TOWN% товар, о котором не спрашивают. %DEF% заплатили молча.", "В %TOWN% шумная ночь: %ATT% продают, %DEF% скупают. Что — лучше не знать.", "Говорят, %DEF% берут товар у %ATT% в %TOWN%. Все знают, никто не говорит." },
    slaves_freed    = { "%ATT% разбили колонну рабов %DEF% и всех отпустили.", "Слыхал, %ATT% освободили рабов %DEF%." },
    succession_crisis = { "%ATT% грызутся за власть.", "У %ATT% нет главного. Ножи наголо." },
    succession_resolved = { "У %ATT% новый хозяин.", "Свара у %ATT% кончилась. Новый главный." },
    faction_split   = { "%ATT% откололись от %DEF%.", "%DEF% раскололись — %ATT% теперь сами по себе." },
    warlord_rose    = { "Какой-то варлорд собирает людей — зовут себя %ATT%.", "Варлорд сколачивает банду из недовольных %DEF%." },
    chaos_cult      = { "В %TOWN% странные сектанты. Шепчут о тёмных богах.", "В %TOWN% завелась какая-то мерзость. Люди пропадают по ночам." },
    base_raid       = { "%ATT% всё говорят о новом поселении. Хотят то, что там лежит.", "%ATT% собираются ударить по поселению Безымянных." },
    base_campaign   = { "%ATT% всё говорят о новом поселении. Хотят то, что там лежит.", "%ATT% собираются ударить по поселению Безымянных." },   -- U2: рейд-кампания движка
    recruit_merc_hired   = { "%LEADER% из %ATT% нанял клинки %DEF% у %TOWN%. Бей, когда контракт кончится.", "%ATT% заплатили %DEF%, чтобы стеречь %LEADER%. Говорят, на два дня." },   -- X2
    recruit_merc_left    = { "Наёмники %DEF% ушли от %LEADER% (%ATT%). Контракт кончился.", "%LEADER% снова ходит без охраны. %DEF% ушли." },
    recruit_slave_bought = { "%ATT% купили лучшего раба в %TOWN% — %LEADER%. Другим не досталось.", "Самый крепкий в клетках %TOWN%, %LEADER%? Его первыми забрали %ATT%." },
    recruit_slave_freed  = { "%LEADER%, купленный %ATT%, на свободе. Кто-то сбил цепи.", "Слыхал? %LEADER% ушёл из цепей %ATT%. Кто-то помог." },
    ally_joins      = { "%ATT% выступили против %DEF% вместе с какими-то бродягами.", "%ATT% ввязались в драку с %DEF%." },
    relic_salvage   = { "%ATT% вытащили из руин что-то древнее. Оно до сих пор гудит.", "Говорят, %ATT% нашли тайник древних." },
    elite_seen      = { "%ATT% вывели свою гвардию у %TOWN%. Тяжёлая броня, холодные глаза.", "У %TOWN% видели элиту %ATT%. Лучше обойти стороной." },
    stock_shortage  = { "В %TOWN% кончается %CAT%. Цены лезут вверх.", "В %TOWN% %CAT% не достать ни за какие деньги." },
    stock_glut      = { "%TOWN% завалили: %CAT% отдают за бесценок.", "В %TOWN% столько, что не знают куда девать — %CAT%. Самое время покупать." },
    stock_sacked    = { "%ATT% вынесли из %TOWN% всё подчистую — склады, лавки, всё.", "Склады %TOWN% разграбили %ATT%." },
    town_shortage   = { "Мастера в %TOWN% сидят без дела — нет сырья: %CAT%.", "В мастерских %TOWN% не хватает: %CAT%." },
    smuggle_run     = { "Контрабандисты протащили в %TOWN% партию: %CAT%. Дорого, зато есть.", "Ночью в %TOWN% провезли %CAT% мимо стражи. Лишних вопросов не задавай." },
    contraband_caught = { "Стража %ATT% поймала бродягу, торговавшего в %TOWN% запретным: %CAT%. Они в ярости.", "Безымянного торговца взяли в %TOWN% с запретным товаром: %CAT%. %ATT% этого не забудут." },
    gear_worn       = { "Патрули %ATT% ходят в ржавой броне. Арсеналы пусты.", "У солдат %ATT% рванина и ржавое железо. Тяжёлые времена." },
    player_sold     = { "Какой-то бродяга сбыл товар в %TOWN%. На %CAT% цены падают.", "Безымянный торговец выгрузил в %TOWN% кучу: %CAT%." },
    caravan_lost    = { "Караван %ATT% так и не дошёл. Волки, бандиты — кто знает.", "%ATT% потеряли торговый караван на дороге. Тела у колеи." },
    refugees        = { "Беженцы из %TOWN% на дорогах. Голодные.", "Целые семьи ушли из %TOWN% с тем, что смогли унести." },
    relic_forge_known = { "Говорят, Безымянные собрали машинный разум древних.", "Ходят слухи, что какие-то бродяги собрали мыслящую машину. Безумцы или гении." },
    trade_for       = { "%ATT% скупают %CAT% у %DEF% по любой цене.", "Караваны %ATT% везут %CAT% от %DEF%. Платят сполна." },
    raid_surplus    = { "%ATT% вернулись из %TOWN% гружёные: %CAT%.", "После налёта на %TOWN% у %ATT% добра — девать некуда: %CAT%." },
    waylay          = { "%ATT% грабят на дорогах людей %DEF%. Без охраны лучше не ходить.", "Караваны %DEF% пропадают один за другим; шепчутся, что %ATT% сидят в засаде у тракта." },
    loot_sold       = { "В %TOWN% кто-то сбывает награбленное: %CAT%, дёшево и без лишних вопросов.", "Говорят, в %TOWN% %ATT% продают свою добычу. Больше всего: %CAT%." },
    cats = { food = "еда", metal = "металл", weapons = "оружие", armor = "броня", med = "лекарства", drugs = "дурь", lux = "роскошь", scrap = "скрап", goods = "товар" },
    chaos_incursion = { "У %TOWN% разорвалось небо. Оттуда вылезли рогатые твари.", "У %TOWN% демоны. Я не шучу." },
    some_leader = "какой-то важный тип", some_faction = "кто-то", far = "где-то далеко на %DIR%",
    dirs = { n = "севере", s = "юге", e = "востоке", w = "западе" },
    hedge = { " Так говорят.", " Только я тебе этого не говорил.", "" },
    herald = "Путники с дороги рассказывают: ",
    msg = "Слух (%WHO%): %TEXT%",
    nemesis_contempt   = { "%LEADER% поймал Безымянных с пустыми карманами и отпустил ползти дальше. Не стоят хлопот, говорит.",
                           "Говорят, %LEADER% плюнул Безымянным под ноги и ушёл. Приходите, когда будет что взять, — так и сказал." },
    nemesis_beat_again = { "%LEADER% снова уложил Безымянных в пыль. Уже со счёта сбился.",
                           "Слыхал, %LEADER% опять побил Безымянных. %ATT% пьют за это каждый вечер." },
    trade_route     = { "Караваны %ATT% теперь ходят в %TOWN%. Торгуют с %DEF%.", "Новый торговый путь в %TOWN%: %ATT% и %DEF% ведут дела." },
    loot_carried = { "Мимо прошли %ATT% — тащили добычу после драки.", "%ATT% волокут добро с поля боя на рынок." },
    merged = " И уже не в первый раз.",
    place_dir = "одно место на %DIR%", place_any = "где-то в пустошах",
    journal_owner = "Слух", journal_day = "День %d, %s: %s", journal_day0 = "День %d: %s",
    small = {
      owner = { "Здесь правят %OWNER%. Их закон, их цены.", "Это земля %OWNER%. Веди себя тихо." },
      low   = { "%CAT% тут нынче в цене. Прилавки почти пустые.", "%CAT% в этом городе не найти. Всем не хватает." },
      high  = { "%CAT% на прилавках завались. Дёшево, для разнообразия.", "Торговцы тут сидят на горах: %CAT%." },
      outlaw = { "За голову %NAME% дают %BOUNTY%. Видели в этих краях.", "%NAME% видели неподалёку. %BOUNTY% за голову." },
      refugees = { "По дороге прошли беженцы. Голодные и молчаливые." },
      caravan = { "Недавно прошёл караван. Охрана нервничала." },
      column = { "Мимо прошла колонна %FAC%. Спешили." },
      courier = { "Гонец %FAC% пронёсся во весь опор. Что-то стряслось." },
      traveler = { "Опять бродяги на дороге. Что ни неделя — больше." },
      quiet = { "Тихая неделя. Караваны приходят, караваны уходят.", "Ничего тут не происходит. Нам так и нравится.", "Та же пыль, те же лица. Покупай или иди дальше." },
    },
  },
}

----------------------------------------------------------------------- СОСТОЯНИЕ
_G.KMM_Rumors = _G.KMM_Rumors or {}
local R = _G.KMM_Rumors
R.events = R.events or {}          -- event_id -> событие (последняя строка с этим id)
R.order = R.order or {}            -- порядок event_id
R.told = R.told or {}              -- "event_id|town" -> true (сказано в town); "event_id|=town" — слито с рассказанным (V6). Рассказано = любой ключ с этим id
R.townLastHour = R.townLastHour or {}   -- начало окна города (игровые часы)
R.townCount = R.townCount or {}         -- слухов в текущем окне города
R.smallHour = R.smallHour or {}         -- V4: когда город последний раз говорил мелочь
R.vstat = R.vstat or { journal = 0, small = 0, journal_fail = 0 }   -- B1 метрика (за сессию)
R.fileSize = R.fileSize or -1
R.lastCheck = R.lastCheck or 0

local okTowns, TOWNS = pcall(require, "kmm_rumors_towns")
if not okTowns or type(TOWNS) ~= "table" then TOWNS = {}; print(TAG .. "town table not loaded: " .. tostring(TOWNS)) end

local function log(line)
  local ok, f = pcall(io.open, CFG.LOG_PATH, "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S") .. "\t" .. line .. "\n"); f:close() end
  print(TAG .. line)
end

-- HEALTH: отказы идут в реестр KMM_Gov (ключи KMM_Rumors.tick|map|journal|<обработчик>): пауза 60/300/1800 с и повтор; без Gov - до перезапуска.
local HPK, HTR = {}, {}
local function HG() local g = rawget(_G, "KMM_Gov"); if type(g) == "table" and type(g.h_fail) == "function" then return g end end
-- отказ: t[f] = true; пауза реестра -> вернёт секунды (флаг снимет h_live), иначе nil
local function h_down(t, f, key, err)
  t[f] = true; HPK[key], HTR[key] = nil, nil
  local g, p = HG(), nil
  if g then local ok, r = pcall(g.h_fail, key, err); if ok and type(r) == "number" then p = r end end
  if p then HPK[key] = true end
  return p
end
-- true = выключено сейчас; пауза истекла -> флаг снят, одна попытка
local function h_live(t, f, key)
  if not t[f] then return false end
  if HPK[key] then
    local g = HG()
    local ok, up = pcall(g and g.h_up or function() return true end, key)
    if (not ok) or up ~= false then t[f] = nil; HPK[key] = nil; HTR[key] = true; return false end
  end
  return true
end
local function h_done(key) if HTR[key] then HTR[key] = nil; local g = HG(); if g then pcall(g.h_ok, key) end end end
local function h_msg(what, p, err) return what .. (p and (" failed, retry in " .. p .. " s: ") or " disabled until restart: ") .. tostring(err) end

local function gameHours()
  local ok, h = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalHours() end)
  return ok and h or nil
end

local function vec(v)  -- Vector3 приходит таблицей или userdata
  if not v then return nil end
  local ok, x, z = pcall(function() return v.x or v[1], v.z or v[3] end)
  if ok and x and z then return x, z end
  return nil
end

----------------------------------------------------------------------- ХРОНИКА
local function split(line)
  local t = {}
  for field in (line .. "\t"):gmatch("([^\t]*)\t") do t[#t + 1] = field end
  return t
end

local function readChronicle()
  local ok, f = pcall(io.open, CFG.CHRONICLE_PATH, "r")
  if not (ok and f) then return end
  local size = f:seek("end")
  if size == R.fileSize then f:close(); return end
  f:seek("set", 0)
  local n = 0
  for line in f:lines() do
    line = line:gsub("\r$", "")
    local c = split(line)
    if #c >= 11 and tonumber(c[1]) then
      local e = { day = tonumber(c[1]), id = c[2], type = c[3], town_sid = c[4], town = c[5], att = c[6], def = c[7],
                  leader_sid = c[8], leader = c[9], status = c[10], text = c[11] }
      if e.type ~= "materialized" then              -- materialized = подтверждение применения, не новое событие
        if not R.events[e.id] then R.order[#R.order + 1] = e.id end
        R.events[e.id] = e
        n = n + 1
      end
    end
  end
  f:close()
  R.fileSize = size
  R.src = "file"
  log(string.format("chronicle read: %d event lines, %d known events", n, #R.order))
end

-- Источник событий текущего мира: журнал дирижёра в памяти (KMM_Conductor.state(); он живёт в сейве этого мира).
-- chronicle.log общий для всех игр, и id событий в новом мире снова начинаются с 1, поэтому файл — только запасной
-- источник, если KMM_Conductor не загружен.
local function readConductor()
  local ok, S = pcall(function() return KMM_Conductor and KMM_Conductor.state and KMM_Conductor.state() end)
  if not (ok and type(S) == "table" and type(S.events) == "table") then return false end
  local events, order = {}, {}
  for _, ev in ipairs(S.events) do
   if not (ev.type == "deed" and ev.witnessed == false) then   -- Y1: дело игрока без свидетелей не становится слухом
    local id = tostring(ev.id)
    events[id] = { day = ev.day or 0, id = id, type = ev.type, town_sid = ev.town_sid or "", town = ev.town_name or "",
                   att = ev.attacker or "", def = ev.defender or "", leader_sid = ev.leader_sid or "", leader = ev.leader_name or "",
                   status = ev.status or "", cat = ev.cat or "", text = (type(ev.text) == "string" and #ev.text < 300) and ev.text or "", a = ev.a, b = ev.b, fid = ev.fid,
                   x = tonumber(ev.x), z = tonumber(ev.z),    -- R2: точка события (место боя и т.п.) для метки на карте
                   kind = ev.kind, by_player = ev.by_player and true or nil }   -- V6: вид дела ядра (слияние однотипного шума)
    order[#order + 1] = id
   end
  end
  R.events, R.order, R.src = events, order, "conductor"
  return true
end

----------------------------------------------------------------------- НОВОСТИ: место события, задержка, вестники
R.heard = R.heard or {}            -- event_id -> true: весть уже принёс вестник (сохраняется в told-списке строкой "@id")

local function townXZ(sid)
  if not sid or sid == "" then return nil end
  local okc, info = pcall(function() local C = rawget(_G, "KMM_Conductor"); local c = C and C.cfg and C.cfg(); return c and c.town_info and c.town_info[sid] end)
  if okc and type(info) == "table" and info.x then return info.x, info.z end
  local tp = TOWNS[sid]
  if tp and tp.x then return tp.x, tp.z end
  return nil
end

-- как Traces.event_xz: город события, иначе позиция фракции (b, a, fid)
local function eventXZ(e)
  local x, z = townXZ(e.town_sid)
  if x then return x, z end
  local C = rawget(_G, "KMM_Conductor")
  if C and C.fpos then
    for _, k in ipairs({ "b", "a", "fid" }) do
      local fid = e[k]
      if fid then
        local ok, fx, fz = pcall(C.fpos, fid)
        if ok and fx then return fx, fz end
      end
    end
  end
  return nil
end

-- задержка новости (дни) от места события до точки (px,pz); без координат -> общая задержка
local function newsDelay(e, ex, ez, px, pz)
  if not (ex and px) then return CFG.NEWS_NOCOORD_DAYS, nil end
  local d = math.sqrt((ex - px) ^ 2 + (ez - pz) ^ 2)
  local days = d / CFG.NEWS_SPEED / (CFG.BIG_SPEED_MULT[e.type] or 1)
  if days > CFG.NEWS_MAX_DAYS then days = CFG.NEWS_MAX_DAYS end
  return days, d
end

-- вестники: путники Traces рядом с игроком; их место-источник (город from, иначе точка выхода) знает новости в радиусе HERALD_NEWS_RADIUS
local function scanHeralds(lx, lz)
  local T = rawget(_G, "KMM_Traces")
  if not (T and T.travelers and lx) then return 0 end
  local ok, list = pcall(T.travelers)
  if not (ok and type(list) == "table") then return 0 end
  local n = 0
  for _, t in ipairs(list) do
    local x, z = t.lx or t.sx, t.lz or t.sz
    if type(t) == "table" and x and (x - lx) ^ 2 + (z - lz) ^ 2 <= CFG.HERALD_RADIUS ^ 2 then
      local ox, oz = townXZ(t.from)
      if not ox then ox, oz = t.sx, t.sz end
      if ox then
        for _, id in ipairs(R.order) do
          local e = R.events[id]
          if e and not R.heard[id] then
            local ex, ez = eventXZ(e)
            if ex and (ex - ox) ^ 2 + (ez - oz) ^ 2 <= CFG.HERALD_NEWS_RADIUS ^ 2 then R.heard[id] = true; n = n + 1 end
          end
        end
      end
    end
  end
  if n > 0 then log("heralds brought news of " .. n .. " events") end
  return n
end

----------------------------------------------------------------------- ИСКАЖЕНИЕ
local function roleOf(ch)
  local ok, name = pcall(function() return ch.data and ch.data.name or ch:getName() end)
  name = (ok and name or ""):lower()
  for _, r in ipairs(CFG.ROLES) do
    for _, m in ipairs(r.match) do
      if name:find(m, 1, true) then return r.level, r.prefer, name, r.kind end
    end
  end
  return CFG.DEFAULT_LEVEL, 0, name, "default"
end

local function direction(fromX, fromZ, toX, toZ)
  local dx, dz = toX - fromX, toZ - fromZ
  if math.abs(dx) > math.abs(dz) then return dx > 0 and "e" or "w" end
  return dz > 0 and "s" or "n"   -- в Kenshi север — отрицательный z (не проверено; при ошибке поменять местами)
end

----------------------------------------------------------------------- V6 ЧИСТЫЕ ИМЕНА: никаких иероглифов и служебных хвостов в тексте
-- Допустимы ASCII, латиница-1/расширенная (U+00A0..U+024F), типографская пунктуация (U+2010..U+2027), при LANG=ru — кириллица.
-- Прочее (CJK и т.п.) — «грязный» отрезок: в имени места имя целиком заменяется описанием («a place to the north»),
-- в готовом тексте события — только сам отрезок. Служебное: «(defunct and broken)», хвостовой номер « 103».
local function cpAt(s, i)
  local c = s:byte(i)
  if c < 0x80 then return c, 1 end
  local b2, b3, b4 = s:byte(i + 1, i + 3)
  if c >= 0xF0 then return (c % 8) * 262144 + ((b2 or 128) % 64) * 4096 + ((b3 or 128) % 64) * 64 + (b4 or 128) % 64, 4 end
  if c >= 0xE0 then return (c % 16) * 4096 + ((b2 or 128) % 64) * 64 + (b3 or 128) % 64, 3 end
  if c >= 0xC0 then return (c % 32) * 64 + (b2 or 128) % 64, 2 end
  return 0xFFFD, 1   -- оборванный байт продолжения
end
local function okCp(cp)
  if cp < 0x80 or (cp >= 0xA0 and cp <= 0x24F) or (cp >= 0x2010 and cp <= 0x2027) then return true end
  return CFG.LANG == "ru" and cp >= 0x400 and cp <= 0x4FF
end
local DIRTY = "\1"
local function markDirty(s)   -- грязные символы -> \1; соседние грязные отрезки (через пробелы) -> один
  local out, i, n, any = {}, 1, #s, false
  while i <= n do
    local cp, len = cpAt(s, i)
    if okCp(cp) then out[#out + 1] = s:sub(i, i + len - 1) else out[#out + 1] = DIRTY; any = true end
    i = i + len
  end
  if not any then return s, false end
  local r = table.concat(out):gsub("\1[%s\1]*\1", "\1")
  return r, true
end
local function stripService(s)
  s = s:gsub("%s*%b()", "")       -- «(defunct and broken)» и подобные пометки редактора
  s = s:gsub("%s+%d+$", "")       -- хвостовой номер экземпляра
  return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end
local function placeDesc(dir)
  local L = T[CFG.LANG] or T.en
  if dir and L.dirs[dir] then return (L.place_dir:gsub("%%DIR%%", L.dirs[dir])) end
  return L.place_any
end
-- имя места/фракции/лидера: чистое имя или fallback (описание места, «someone»...)
local function cleanName(s, fallback)
  if type(s) ~= "string" or s == "" or s == "?" then return fallback, true end
  local m, dirty = markDirty(s)
  if dirty then return fallback, true end
  m = stripService(m)
  if m == "" then return fallback, true end
  return m, m ~= s
end
-- готовый текст: грязные отрезки -> описание места, служебные пометки места убраны, первая буква заглавная
local function cleanText(s, dir)
  if type(s) ~= "string" or s == "" then return s, false end
  local m, dirty = markDirty(s)
  local s2 = m:gsub("%s*%([^)]*defunct[^)]*%)%s*%d*", ""):gsub("%s*%([^)]*broken[^)]*%)%s*%d*", "")
  if dirty then
    local desc = placeDesc(dir):gsub("%%", "%%%%")
    s2 = s2:gsub("\1", desc)
  end
  s2 = s2:gsub("^%l", string.upper)
  return s2, s2 ~= s
end
R.clean = { name = cleanName, text = cleanText, place = placeDesc }   -- офлайн-тест

-- слух можно сложить из события: есть шаблон, или тип внешнего модуля с готовым текстом
local PFX = { "fate_", "relic_", "predator_", "siege_", "herd", "veteran", "bounty_hunters", "slave_caravan", "famine_refugees", "outlaw_", "nemesis_", "debt_", "deed", "base_raid_", "recruit_", "settlement_", "goal_milestone", "lie_low" }   -- deed: дела мира из KMM_Deeds (ядро affectRelations); B1: settlement_/goal_milestone/lie_low — готовый текст мира
local NON_TYPE = { cats = true, dirs = true, hedge = true, small = true, wrap = true }   -- служебные таблицы текстов, не типы событий
local function tellable(e)
  local L = T[CFG.LANG] or T.en
  local kind = tostring(e.type)
  if type(L[kind]) == "table" and not NON_TYPE[kind] then return true end
  if not (e.text and e.text ~= "") then return false end
  for _, p in ipairs(PFX) do if kind:sub(1, #p) == p then return true end end
  return false
end

----------------------------------------------------------------------- B1 ФОРМЫ РЕЧИ: годовой учёт по ключу «тип#номер»
-- R.forms[key] = игровой день, когда форма прозвучала. Свободна, если не звучала FORM_YEAR_DAYS (или время ушло назад).
-- Выбор среди свободных — с весом по манере рассказчика (CFG.MANNER). Свободных нет — слух этого типа не говорится (nil).
R.forms = R.forms or {}
local function formFree(key, day)
  local last = R.forms[key]
  return not (last and day and day >= last and day - last < CFG.FORM_YEAR_DAYS)
end
local function pickForm(n, kind, rkind, day)
  local w = CFG.MANNER[rkind or "default"] or CFG.MANNER.default
  local opts, tot = {}, 0
  for i = 1, n do
    if formFree(kind .. "#" .. i, day) then
      local wi = w[i] or w[2] or 1
      opts[#opts + 1] = { i, wi }; tot = tot + wi
    end
  end
  if #opts == 0 then return nil end
  local r = math.random() * tot
  for _, o in ipairs(opts) do r = r - o[2]; if r <= 0 then return o[1] end end
  return opts[#opts][1]
end
-- годовой учёт: старше года — долой, сверх FORMS_MAX — самые старые
local function pruneForms(day)
  local keys = {}
  for k, d in pairs(R.forms) do
    if type(d) ~= "number" or (day and (day - d >= CFG.FORM_YEAR_DAYS or d > day + 1)) then R.forms[k] = nil else keys[#keys + 1] = k end
  end
  local cut = 0
  if #keys > CFG.FORMS_MAX then
    table.sort(keys, function(a, b) if R.forms[a] ~= R.forms[b] then return R.forms[a] < R.forms[b] end return a < b end)
    for i = 1, #keys - CFG.FORMS_MAX do R.forms[keys[i]] = nil; cut = cut + 1 end
  end
  return cut
end
R.formsfn = { free = formFree, pick = pickForm, prune = pruneForms }   -- офлайн-тест

-- текст слуха: (текст, тип, ключ формы) или nil, reason ("forms_used" — все формы типа звучали за год)
local function compose(e, level, dist, dir, merged, rkind, day)
  local L = T[CFG.LANG] or T.en
  local kind = e.type
  if level >= 2 and math.random() < CFG.WRONG_OUTCOME_CHANCE then
    local swap = { leader_killed = "leader_captured", leader_captured = "leader_killed", attack_repelled = "leader_killed",
                   treaty_signed = "betrayal", treaty_broken = "betrayal", mobilized = "raid", ally_help = "ally_failed", faction_decline = "faction_fell" }
    kind = swap[kind] or kind
  end
  local pool = L[kind]
  local tail = (merged and merged > 1 and L.merged) or ""   -- V6: слитая группа однотипного шума
  local function esc(x) return (tostring(x):gsub("%%", "%%%%")) end   -- % в подстановке gsub
  if type(pool) ~= "table" or NON_TYPE[kind] then   -- ЖИВОЙ МИР (2026-11-13): типы внешних модулей без шаблона — готовый текст события (en) в форме-обёртке
    if not tellable({ type = kind, text = e.text }) then return nil end
    local wrap = L.wrap or T.en.wrap
    local fi = pickForm(#wrap, kind, rkind, day)
    if not fi then return nil, "forms_used" end
    local s0 = wrap[fi]:gsub("%%TEXT%%", esc(cleanText(e.text, dir)))
    s0 = s0 .. tail
    if level >= 1 and L.hedge and fi ~= 2 then s0 = s0 .. L.hedge[math.random(#L.hedge)] end
    return s0, kind, kind .. "#" .. fi
  end
  local fi = pickForm(#pool, kind, rkind, day)
  if not fi then return nil, "forms_used" end
  local s = pool[fi]
  local leader = cleanName(e.leader, L.some_leader)
  if level >= 1 then leader = L.some_leader end
  local town = cleanName(e.town, placeDesc(dir))
  if (level >= 2 or (dist and dist > CFG.FAR_DISTANCE)) and dir then town = L.far:gsub("%%DIR%%", L.dirs[dir]) end
  local att = cleanName(e.att, L.some_faction)
  local def = cleanName(e.def, L.some_faction)
  if level >= 2 and math.random() < 0.5 then if math.random() < 0.5 then att = L.some_faction else def = L.some_faction end end   -- путает, кто это был
  s = s:gsub("%%LEADER%%", esc(leader)):gsub("%%TOWN%%", esc(town)):gsub("%%ATT%%", esc(att)):gsub("%%DEF%%", esc(def))
  local cats = L.cats or {}
  s = s:gsub("%%CAT%%", esc(cats[e.cat or ""] or cats.goods or "goods"))
  s = cleanText(s, dir) .. tail   -- страховка: в шаблон ничего грязного не просочилось
  if level >= 1 and fi ~= 2 then s = s .. L.hedge[math.random(#L.hedge)] end
  return s, kind, kind .. "#" .. fi
end

----------------------------------------------------------------------- ДОСТАВКА
local function playerInTown()
  local ok, chars = pcall(function() return getPlayerInterface():getAllPlayerCharacters() end)
  if not ok or not chars then return nil end
  for _, c in pairs(chars) do
    local okT, town = pcall(function() return c:getCurrentTownLocation() end)
    local okD, dead = pcall(function() return c:isDead() end)
    if okT and town and not (okD and dead) then return c, town end
  end
  return nil
end

local function townKey(town)
  local ok, n = pcall(function() return town:getName() end)
  if ok and n and n ~= "" then return n end
  local okP, x, z = pcall(function() return vec(town:getPosition()) end)
  if okP and x then return string.format("%d_%d", math.floor(x / 1000), math.floor(z / 1000)) end
  return "?"
end

-- V2: разные рассказчики. Рассказчик дня (имя) с SPEAKER_MAX_DAY слухами пропускается; уже говоривший в этом визите — штраф.
-- Без учёта (R.spk = nil, команды консоли) — без штрафа.
local function speakerName(ch)
  local ok, n = pcall(function() return ch:getName() end)
  return (ok and type(n) == "string") and n or "?"
end
local function speakerPenalty(ch)
  local sp = R.spk
  if not sp then return 0 end
  local nm = speakerName(ch)
  if (sp.n[nm] or 0) >= CFG.SPEAKER_MAX_DAY then return nil end
  return ((R.visit and R.visit.spk[nm]) or 0) * 12000   -- больше разницы ролей (prefer x 10000): второй слух — у другого, если он есть
end

-- Снимок загруженных NPC (PERF): KMM_Gov.snapshot(ttl), без Gov/при ошибке — прежний обход списка (фолбэк ниже).
local function findSpeakerSnap(listener, lx, lz)
  local g = rawget(_G, "KMM_Gov")
  if not (g and g.snapshot) then return nil, false end
  local ok, snap = pcall(g.snapshot, 5)
  if not (ok and snap) then return nil, false end
  local best, bestScore
  for _, r in ipairs(snap.list) do
    if not r.dead then
      local d = math.sqrt((r.x - lx) ^ 2 + (r.z - lz) ^ 2)
      if d <= CFG.TALK_RADIUS and r.town then
        local alive = true
        pcall(function() if r.ch:isDead() then alive = false end end)   -- снимок мог устареть
        local pen = alive and speakerPenalty(r.ch)
        if alive and pen then
          local level, prefer = roleOf(r.ch)
          local score = prefer * 10000 - d - pen
          if not bestScore or score > bestScore then best, bestScore = r.ch, score end
        end
      end
    end
  end
  return best, true
end

local function findSpeaker(listener)
  local lx, lz = vec(listener:getPosition())
  if not lx then return nil end
  local okS, sp, used = pcall(findSpeakerSnap, listener, lx, lz)
  if okS and used then return sp end
  local ok, list = pcall(function() return getGameWorld():getCharacterUpdateList() end)
  if not ok or not list then return nil end
  local best, bestScore
  for c in pairs(list) do
    local good = pcall(function()
      if c:isPlayerCharacter() or c:isDead() or not c:getCurrentTownLocation() then return end
      local x, z = vec(c:getPosition())
      if not x then return end
      local d = math.sqrt((x - lx) ^ 2 + (z - lz) ^ 2)
      if d > CFG.TALK_RADIUS then return end
      local pen = speakerPenalty(c)
      if not pen then return end
      local level, prefer = roleOf(c)
      local score = prefer * 10000 - d - pen
      if not bestScore or score > bestScore then best, bestScore = c, score end
    end)
  end
  return best
end

----------------------------------------------------------------------- КАРТА (R2): слух — наводка на ванильной карте
-- Слух о месте (город, руина, лагерь, логово, место боя) открывает его: TownBase:setDiscovered(true) + setRecentlyDiscovered(true)
-- — родной маркер «новое место». Слух о живом разыскиваемом/сопернике (запись KMM_Outlaws с живым отрядом рядом) показывает
-- его отряд: ManagementScreen.getSingleton():addSquadToMap(Platoon) на MAP.SQUAD_HOURS, потом removeSquadFromMap.
-- Объект места: TownList (SharedKing) из Lua недостижим (docs/core/world.md), поэтому город ищется как в KMM_Traces:
-- Faction.warMgr:getNearestTown(pos) у фракций события (хозяин города, b, a, fid, MAP.EXTRA_FIDS) + проверка расстояния
-- до точки слуха (MATCH_RADIUS). Место без такой фракции (ничьи руины) не находится — пишется miss reason=no_town.
-- Только точные слухи (уровень искажения < 2, не «где-то далеко»). Ошибка вызова движка выключает только карту.
CFG.MAP = {
  ON              = true,
  MAX_PLACES_DAY  = 3,       -- новых мест на карте за игровой день (уже открытые не считаются)
  MAX_SQUADS_DAY  = 1,       -- отрядов на карте за игровой день
  MAX_SQUADS_LIVE = 2,       -- одновременно на карте
  SQUAD_HOURS     = 24,      -- сколько игровых часов отряд виден
  MATCH_RADIUS    = 3000,    -- найденный город должен быть ближе стольких ед. к месту слуха
  EXTRA_FIDS      = {},      -- доп. фракции-хозяева мест (stringID), если их нет в событии
  SQUAD_TYPES     = { "outlaw_", "nemesis_" },
}
R.map = R.map or { day = -1, places = 0, squads = 0, live = {} }

local function mapOff(where, err)
  local p = h_down(R.map, "off", "KMM_Rumors.map", err)
  local m = p and ("map failed in " .. where .. ", retry in " .. p .. " s: " .. tostring(err)) or ("map disabled until restart in " .. where .. ": " .. tostring(err))
  log(m)
  local okf, f = pcall(io.open, "C:/KenshiModMap/logs/debug.log", "a")
  if okf and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Rumors] ", m, "\n"); f:close() end
end

-- фракции, у которых искать город места: хозяин города по дирижёру, стороны события, доп. список
local function placeFids(e)
  local out, seen = {}, {}
  local function add(f) if type(f) == "string" and f ~= "" and not seen[f] then seen[f] = true; out[#out + 1] = f end end
  local C = rawget(_G, "KMM_Conductor")
  if e.town_sid and e.town_sid ~= "" and C and C.towns then
    local ok, list = pcall(C.towns)
    if ok and type(list) == "table" then for _, t in ipairs(list) do if t.sid == e.town_sid then add(t.owner); break end end end
  end
  add(e.b); add(e.a); add(e.fid)
  for _, f in ipairs(CFG.MAP.EXTRA_FIDS or {}) do add(f) end
  return out
end

-- ближайший к (x,z) город фракций события в пределах MATCH_RADIUS: TownBase, fid, расстояние
local function findPlace(e, x, z)
  local best, bfid, bd
  for _, fid in ipairs(placeFids(e)) do
    local ok, t = pcall(function()
      local f = getGameWorld().factionMgr:getFactionByStringID(fid)
      return f and f.warMgr and f.warMgr:getNearestTown({ x = x, y = 0, z = z })
    end)
    if ok and t then
      local okP, tx, tz = pcall(function() return vec(t:getPosition()) end)
      if okP and tx then
        local d = math.sqrt((tx - x) ^ 2 + (tz - z) ^ 2)
        if d <= CFG.MAP.MATCH_RADIUS and (not bd or d < bd) then best, bfid, bd = t, fid, d end
      end
    end
  end
  return best, bfid, bd
end

local function mapPlace(e)
  local x, z = e.x, e.z
  if not (x and z) then x, z = townXZ(e.town_sid) end
  if not x then log("map place miss event=" .. tostring(e.id) .. " type=" .. tostring(e.type) .. " reason=no_xz"); return end
  local t, fid, d = findPlace(e, x, z)
  if not t then log(string.format("map place miss event=%s type=%s reason=no_town xz=%.0f,%.0f", tostring(e.id), tostring(e.type), x, z)); return end
  local name = townKey(t)
  if t:isDiscovered() then log(string.format("map place known event=%s type=%s place=%s", tostring(e.id), tostring(e.type), name)); return end
  if R.map.places >= CFG.MAP.MAX_PLACES_DAY then log(string.format("map place limit event=%s place=%s day_n=%d", tostring(e.id), name, R.map.places)); return end
  t:setDiscovered(true)
  t:setRecentlyDiscovered(true)
  R.map.places = R.map.places + 1
  local okV, now = pcall(function() return t:isDiscovered() end)
  log(string.format("map place %s event=%s type=%s place=%s fid=%s d=%.0f day_n=%d", (okV and now) and "ok" or "FAIL",
    tostring(e.id), tostring(e.type), name, tostring(fid), d, R.map.places))
end

local function squadType(kind)
  for _, p in ipairs(CFG.MAP.SQUAD_TYPES) do if kind:sub(1, #p) == p then return true end end
  return false
end

-- запись KMM_Outlaws по имени (как Nemesis.find: имя, прежнее имя, прозвища) и её живой отряд (live["o"..i].pl), если он рядом
local function findOutlaw(name)
  local O = rawget(_G, "KMM_Outlaws")
  if not (O and O.wanted and O.live) then return nil end
  local okW, list = pcall(O.wanted)
  local okL, live = pcall(O.live)
  if not (okW and type(list) == "table") then return nil end
  for _, o in ipairs(list) do
    local hit = o.n == name or (o.pg and o.pg.base == name)
    if not hit and o.pg and o.pg.aka then for _, a in ipairs(o.pg.aka) do if a == name then hit = true; break end end end
    if hit then return o, (okL and type(live) == "table") and live["o" .. tostring(o.i)] or nil end
  end
  return nil
end

local function mapSquad(e, now)
  local kind = tostring(e.type)
  if not squadType(kind) or (e.leader or "") == "" or e.status == "dead" or kind:find("dead", 1, true) then return end
  local o, lv = findOutlaw(e.leader)
  if not o then log("map squad miss event=" .. tostring(e.id) .. " name=" .. e.leader .. " reason=no_record"); return end
  if not (lv and lv.pl) then log("map squad miss event=" .. tostring(e.id) .. " name=" .. e.leader .. " reason=not_live"); return end
  local key = "o" .. tostring(o.i)
  local s = R.map.live[key]
  if s then s.untilH = now + CFG.MAP.SQUAD_HOURS; log("map squad extend name=" .. e.leader .. " hours=" .. CFG.MAP.SQUAD_HOURS); return end
  local nlive = 0
  for _ in pairs(R.map.live) do nlive = nlive + 1 end
  if R.map.squads >= CFG.MAP.MAX_SQUADS_DAY or nlive >= CFG.MAP.MAX_SQUADS_LIVE then
    log(string.format("map squad limit name=%s day_n=%d live=%d", e.leader, R.map.squads, nlive)); return
  end
  local MS = rawget(_G, "ManagementScreen")   -- нет класса (стенд/старый RE_Kenshi) = промах, а не самоотключение карты
  local ms = MS and MS.getSingleton and MS.getSingleton()
  if not ms then log("map squad miss event=" .. tostring(e.id) .. " name=" .. e.leader .. " reason=no_screen"); return end
  ms:addSquadToMap(lv.pl)
  R.map.live[key] = { pl = lv.pl, untilH = now + CFG.MAP.SQUAD_HOURS, name = e.leader }
  R.map.squads = R.map.squads + 1
  log(string.format("map squad ok event=%s type=%s name=%s hours=%d", tostring(e.id), e.type, e.leader, CFG.MAP.SQUAD_HOURS))
end

-- снять отряды с истёкшим сроком (или после отката времени). Отряд, исчезнувший из KMM_Outlaws.live (ушёл/убит),
-- не трогаем: указатель мог умереть, removeSquadFromMap на нём опасен
local function mapExpire(now)
  for key, s in pairs(R.map.live) do
    if now >= s.untilH or now + 12 < s.untilH - CFG.MAP.SQUAD_HOURS then
      R.map.live[key] = nil
      local O = rawget(_G, "KMM_Outlaws")
      local okL, live = pcall(function() return O and O.live and O.live() end)
      local lv = okL and type(live) == "table" and live[key]
      if lv and lv.pl == s.pl then
        local ok, err = pcall(function() rawget(_G, "ManagementScreen").getSingleton():removeSquadFromMap(s.pl) end)
        log("map squad off name=" .. tostring(s.name) .. " remove=" .. (ok and "ok" or tostring(err)))
        if not ok then mapOff("expire", err); return end
      else
        log("map squad gone name=" .. tostring(s.name))
      end
    end
  end
end

-- слух реально сказан: место -> карта, разыскиваемый -> его отряд на карте
local function mapHint(e, level, dist, now)
  if not CFG.MAP.ON or h_live(R.map, "off", "KMM_Rumors.map") then return end
  local d = math.floor(now / 24)
  if d ~= R.map.day then R.map.day, R.map.places, R.map.squads = d, 0, 0 end
  if level >= 2 or (dist and dist > CFG.FAR_DISTANCE) then log("map skip event=" .. tostring(e.id) .. " reason=vague level=" .. level); return end
  local ok, err = pcall(mapPlace, e)
  if not ok then mapOff("place", err); return end
  ok, err = pcall(mapSquad, e, now)
  if not ok then mapOff("squad", err) else h_done("KMM_Rumors.map") end
end

----------------------------------------------------------------------- V2 ГЛОБАЛЬНАЯ ПАМЯТЬ РАССКАЗАННОГО
-- R.told хранит ключи "id|town" (формат сейва прежний); рассказанным считается событие с ЛЮБЫМ ключом своего id —
-- одно событие не пересказывают в каждом новом городе. Индекс строится заново на каждой проверке (тесты и загрузка меняют R.told целиком).
-- Значение индекса: "say" — сказано, "merged" — слито с рассказанным (V6), "fail" — say() упал (на экран не дошло).
local function toldIndex()
  local idx = {}
  for k in pairs(R.told) do
    local id, rest = tostring(k):match("^([^|]*)|?(.*)$")
    if id and id ~= "" then
      local v = (rest:sub(1, 1) == "=") and "merged" or ((rest:sub(1, 1) == "!") and "fail" or "say")
      if idx[id] ~= "say" then idx[id] = (v == "say" or not idx[id]) and v or idx[id] end
    end
  end
  return idx
end

----------------------------------------------------------------------- V3 ЖУРНАЛ УСЛЫШАННОГО
-- ManagementScreen.getSingleton():addMessage(owner, msg, MessageLogColor.ML_NORMAL) — вкладка сообщений окна управления (✓код, BindingsReference ManagementScreen).
-- Окна нет (ранняя загрузка) — строка ждёт в очереди; класса нет и SHOW_IN_MESSAGE_LOG — showPlayerAMessage_withLog. Ошибка вызова выключает только журнал.
R.jq = R.jq or {}
R.jday = R.jday or { day = -1, n = 0 }
R.jdone = R.jdone or {}   -- id событий, записанных в журнал за сессию (KMM_Rumors.journaled — для хроники Nemesis)
-- ревью: хроника Nemesis уже записала это событие во вкладку сообщений — не дублировать. KMM_Nemesis.chronicled(event_id) -> bool;
-- нет модуля/функции или ошибка — прежнее поведение. id дирижёра — число, у нас строка: спрашиваем числом, потом строкой
local function chronicled(id)
  local NM = rawget(_G, "KMM_Nemesis")
  local f = type(NM) == "table" and NM.chronicled
  if type(f) ~= "function" then return false end
  local n = tonumber(id)
  local ok, r = pcall(f, n or id)
  if ok and r == true then return true end
  if n ~= nil and type(id) == "string" then
    local ok2, r2 = pcall(f, tostring(id))
    if ok2 and r2 == true then return true end
  end
  return false
end
local function journalFlush()
  if not CFG.JOURNAL_ON or h_live(R, "journalOff", "KMM_Rumors.journal") or #R.jq == 0 then return end
  local MS = rawget(_G, "ManagementScreen")
  if not MS then
    if CFG.SHOW_IN_MESSAGE_LOG then
      local q = table.remove(R.jq, 1)
      local ok, err = pcall(function() getGameWorld():showPlayerAMessage_withLog(q.owner .. ": " .. q.msg, true) end)
      if ok then R.vstat.journal = R.vstat.journal + 1; log("journal ok via=showPlayerAMessage text=" .. q.msg)
      else local p = h_down(R, "journalOff", "KMM_Rumors.journal", err); R.vstat.journal_fail = R.vstat.journal_fail + 1; log(h_msg("journal", p, "showPlayerAMessage_withLog FAILED: " .. tostring(err))) end
    end
    return
  end
  local okS, ms = pcall(function() return MS.getSingleton() end)
  if not (okS and ms) then return end   -- окно ещё не создано — ждём
  local col = rawget(_G, "MessageLogColor")
  local okc, c0 = pcall(function() return col and col.ML_NORMAL end)
  while #R.jq > 0 do
    local q = table.remove(R.jq, 1)
    if chronicled(q.id) then log("journal skip event=" .. tostring(q.id) .. " reason=chronicled"); return journalFlush() end
    local ok, err = pcall(function() ms:addMessage(q.owner, q.msg, (okc and c0) or 0) end)
    if not ok then
      local p = h_down(R, "journalOff", "KMM_Rumors.journal", err); R.vstat.journal_fail = R.vstat.journal_fail + 1
      log(h_msg("journal", p, "addMessage FAILED: " .. tostring(err)))
      return
    end
    R.vstat.journal = R.vstat.journal + 1
    h_done("KMM_Rumors.journal")
    R.jdone[tostring(q.id)] = true
    if not R.journalOkLogged then R.journalOkLogged = true; log("journal: addMessage ok (ManagementScreen message log)") end
    log("journal event=" .. tostring(q.id) .. " owner=" .. q.owner .. " text=" .. q.msg)
  end
end
local function journalAdd(id, who, place, text, day)
  if not CFG.JOURNAL_ON or R.journalOff then return end
  if chronicled(id) then log("journal skip event=" .. tostring(id) .. " reason=chronicled"); return end
  if R.jday.day ~= day then R.jday.day, R.jday.n = day, 0 end
  if R.jday.n >= CFG.JOURNAL_MAX_DAY then log("journal skip event=" .. tostring(id) .. " reason=day_cap"); return end
  R.jday.n = R.jday.n + 1
  local L = T[CFG.LANG] or T.en
  local t = text
  if #t > CFG.JOURNAL_MAX_CHARS then t = t:sub(1, CFG.JOURNAL_MAX_CHARS - 3):gsub("[\128-\191]+$", ""):gsub("[\192-\255]$", "") .. "..." end
  local msg = place and string.format(L.journal_day, day, place, t) or string.format(L.journal_day0, day, t)
  local owner = cleanName(who, L.journal_owner)
  R.jq[#R.jq + 1] = { id = id, owner = owner, msg = msg }
  while #R.jq > CFG.JOURNAL_QUEUE do table.remove(R.jq, 1) end
  journalFlush()
end

----------------------------------------------------------------------- B1 МЕТРИКА ВИДИМОСТИ
-- Доля событий текущего мира (журнал дирижёра), дошедших до экрана через слухи (say ok), по типам.
-- Строка в rumors.log: VISIBILITY day=D events=M shown=N merged=K pct=P journal=J smalltalk=S types=type:shown/total,...
-- shown — сказано пузырём (say ok); merged — слито в сказанный слух (видно как часть его); pct = 100*(shown+merged)/events.
-- types — все типы мира, по убыванию total, при равенстве по имени; shown в типе считает shown+merged.
local function visibility()
  local idx = toldIndex()
  local byT, M, N, K = {}, 0, 0, 0
  for _, id in ipairs(R.order) do
    local e = R.events[id]
    if e then
      local ty = tostring(e.type)
      local b = byT[ty] or { t = 0, s = 0 }
      byT[ty] = b
      b.t = b.t + 1; M = M + 1
      local v = idx[tostring(id)]
      if v == "say" then N = N + 1; b.s = b.s + 1 elseif v == "merged" then K = K + 1; b.s = b.s + 1 end
    end
  end
  local list = {}
  for ty, b in pairs(byT) do list[#list + 1] = { ty, b } end
  table.sort(list, function(a, b) if a[2].t ~= b[2].t then return a[2].t > b[2].t end return a[1] < b[1] end)
  local parts = {}
  for _, p in ipairs(list) do parts[#parts + 1] = string.format("%s:%d/%d", p[1], p[2].s, p[2].t) end
  local pct = M > 0 and (100 * (N + K) / M) or 0
  return { events = M, shown = N, merged = K, pct = pct, types = table.concat(parts, ","), by = byT }
end
local function visLog(force)
  local okV, v = pcall(visibility)
  if not okV then log("visibility failed: " .. tostring(v)); return end
  local h = gameHours()
  local sig = string.format("%d|%d|%d|%d|%d", v.events, v.shown, v.merged, R.vstat.journal, R.vstat.small)
  if not force and sig == R.visSig then return end
  R.visSig = sig
  log(string.format("VISIBILITY day=%d events=%d shown=%d merged=%d pct=%.1f journal=%d smalltalk=%d types=%s",
    h and math.floor(h / 24) or -1, v.events, v.shown, v.merged, v.pct, R.vstat.journal, R.vstat.small, v.types))
end
R.visibility = visibility
R.journaled = function(id) return R.jdone[tostring(id)] == true end   -- для хроники Nemesis: слух уже в журнале

----------------------------------------------------------------------- V4 МЕЛОЧЬ ГОРОДА: в визите не прозвучало новостей — житель говорит о местном
-- Только чтение модели: хозяин города (KMM_Conductor.town_mood/name), полки (KMM_Stock.level), разыскиваемые рядом
-- (KMM_Outlaws.wanted: o.st == "a", o.x/o.z, o.n, o.b), путники рядом (KMM_Traces.travelers). Ничего нет — «тихая неделя».
local function townSid(town)
  local ok, sid = pcall(function() local gd = town:getGameData() or town.data; return gd and gd.stringID end)
  return ok and sid or nil
end
local function pickOne(pool) return pool[math.random(#pool)] end
local function smallLines(tsid, lx, lz)
  local L = T[CFG.LANG] or T.en
  local S = L.small
  local opts = {}
  local function esc(x) return (tostring(x):gsub("%%", "%%%%")) end
  local C = rawget(_G, "KMM_Conductor")
  local food, unrest, short = nil, 0, false   -- состояние города для весов бытовой болтовни
  if tsid and C and C.town_mood then
    local okm, mood = pcall(C.town_mood, tsid)
    local owner = okm and type(mood) == "table" and mood.owner
    if okm and type(mood) == "table" then
      if type(mood.food) == "number" and mood.food == mood.food then food = mood.food end
      unrest = tonumber(mood.unrest) or 0
    end
    local pf
    pcall(function() pf = C.cfg().player_faction end)
    if owner and owner ~= pf and C.name then
      local okn, on = pcall(C.name, owner)
      local nm = okn and cleanName(on, nil)
      if nm and nm ~= owner then opts[#opts + 1] = { "owner", (pickOne(S.owner):gsub("%%OWNER%%", esc((nm:gsub("^The ", "the "))))) } end
    end
  end
  local K = rawget(_G, "KMM_Stock")
  if tsid and K and K.level then
    local cats = L.cats or {}
    for _, cat in ipairs({ "food", "metal", "weapons", "med", "drugs" }) do
      local okl, lv = pcall(K.level, tsid, cat)
      if okl and type(lv) == "number" and lv == lv and lv >= 0 then
        local word = cats[cat] or cat
        if cat == "food" and food == nil then food = lv end
        if lv < CFG.STOCK_LOW then short = true end
        if lv < CFG.STOCK_LOW then opts[#opts + 1] = { "stock_low", (pickOne(S.low):gsub("%%CAT%%", esc(word))) }
        elseif lv > CFG.STOCK_HIGH then opts[#opts + 1] = { "stock_high", (pickOne(S.high):gsub("%%CAT%%", esc(word))) } end
      end
    end
  end
  local O = rawget(_G, "KMM_Outlaws")
  if lx and O and O.wanted then
    local okw, list = pcall(O.wanted)
    if okw and type(list) == "table" then
      local best, bd
      for _, o in ipairs(list) do
        if type(o) == "table" and o.st == "a" and tonumber(o.x) and tonumber(o.z) then
          local d = (o.x - lx) ^ 2 + (o.z - lz) ^ 2
          if d <= CFG.NEAR_OUTLAW_R ^ 2 and (not bd or d < bd) then best, bd = o, d end
        end
      end
      local nm = best and cleanName(best.n, nil)
      if nm then
        local s = pickOne(S.outlaw):gsub("%%NAME%%", esc(nm)):gsub("%%BOUNTY%%", esc(tonumber(best.b) or "a few hundred"))
        opts[#opts + 1] = { "outlaw", s }
      end
    end
  end
  local TR = rawget(_G, "KMM_Traces")
  if lx and TR and TR.travelers then
    local okt, list = pcall(TR.travelers)
    if okt and type(list) == "table" then
      for _, t in ipairs(list) do
        local x, z = type(t) == "table" and (t.lx or t.sx), type(t) == "table" and (t.lz or t.sz)
        if x and z and (x - lx) ^ 2 + (z - lz) ^ 2 <= CFG.NEAR_TRAVELER_R ^ 2 then
          local pool = S[tostring(t.kind)] or S.traveler
          local fac = L.some_faction
          if t.fid and C and C.name then local okn, fn = pcall(C.name, t.fid); fac = (okn and cleanName(fn, nil)) or fac end
          opts[#opts + 1] = { "traveler", (pickOne(pool):gsub("%%FAC%%", esc(fac))) }
          break
        end
      end
    end
  end
  for _, o in ipairs(opts) do o[3] = (o[1] == "owner") and 2 or 3 end   -- местное из модели — весомее болтовни
  -- B1 бытовая болтовня: всегда есть, вес по состоянию города; годовому учёту форм не подлежит (может повторяться)
  local function chat(kind, w) if w > 0 and S[kind] then opts[#opts + 1] = { "chat_" .. kind, pickOne(S[kind]), w } end end
  chat("weather", 1)
  chat("work", (food and food < CFG.STOCK_LOW) and 0.5 or 1)
  if unrest >= 0.5 then chat("tense", 3) else chat("guard", 1) end
  if food and food < CFG.STOCK_LOW then chat("hunger", 3) end
  if short then chat("prices", 2) end
  chat("quiet", (#opts <= 3) and 1 or 0.3)
  return opts
end
local function smallTalk(listener, tkey, tsid, now, lx, lz)
  local opts = smallLines(tsid, lx, lz)
  local L = T[CFG.LANG] or T.en
  local last = R.smallLast and R.smallLast[tkey]
  local pickFrom, tot = {}, 0
  for _, o in ipairs(opts) do if o[1] ~= last then pickFrom[#pickFrom + 1] = o; tot = tot + (o[3] or 1) end end
  if #pickFrom == 0 then pickFrom = opts; for _, o in ipairs(opts) do tot = tot + (o[3] or 1) end end
  local o
  local r = math.random() * tot
  for _, x in ipairs(pickFrom) do r = r - (x[3] or 1); if r <= 0 then o = x; break end end
  o = o or pickFrom[#pickFrom] or { "quiet", pickOne(L.small.quiet) }
  local speaker = findSpeaker(listener)
  if not speaker then return nil end   -- никого рядом — повтор на следующей проверке
  local text = cleanText(o[2])
  local okSay, errSay = pcall(function() speaker:say(text) end)
  R.smallHour[tkey] = now
  R.smallLast = R.smallLast or {}
  R.smallLast[tkey] = o[1]
  if okSay then R.vstat.small = R.vstat.small + 1 end
  log(string.format("smalltalk town=%s kind=%s speaker=%s options=%d say=%s text=%s", tkey, o[1], speakerName(speaker), #opts,
    okSay and "ok" or tostring(errSay), text))
  return okSay
end

local function tryTell()
  local now = gameHours()
  if not now then return end
  journalFlush()
  local listener, town = playerInTown()
  if not listener then R.visit = nil; return end
  local tkey = townKey(town)
  local clk = os.clock()
  if not (R.visit and R.visit.town == tkey) then R.visit = { town = tkey, t0 = clk, told = 0, small = false, spk = {} } end
  local visit = R.visit
  local dayNow = now / 24
  local dayI = math.floor(dayNow)
  if not (R.spk and R.spk.day == dayI) then R.spk = { day = dayI, n = {} } end
  if not (R.noisyDay and R.noisyDay.day == dayI) then R.noisyDay = { day = dayI, n = {} } end
  if not R.townLastHour[tkey] or now - R.townLastHour[tkey] >= CFG.TOWN_COOLDOWN_HOURS or now < R.townLastHour[tkey] then
    R.townLastHour[tkey], R.townCount[tkey] = now, 0          -- новое окно города
  end
  local lx, lz = vec(listener:getPosition())
  local canTell = (R.townCount[tkey] or 0) < CFG.MAX_PER_TOWN and clk - (R.lastTellClock or -1e9) >= CFG.RUMOR_GAP_SEC
  local told = 0
  if canTell then
    pcall(scanHeralds, lx, lz)
    local idx = toldIndex()
    local cands, groups = {}, {}
    for i = #R.order, 1, -1 do                       -- свежие события первыми
      local e = R.events[R.order[i]]
      if e and not idx[tostring(e.id)] and tellable(e) then
        local ex, ez = eventXZ(e)
        local delay, dist = newsDelay(e, ex, ez, lx, lz)
        local herald = R.heard[e.id] and true or false
        if herald then delay = 0 end
        local ageDays = dayNow - (e.day or 0)
        if ageDays >= delay and ageDays <= CFG.MAX_AGE_DAYS then
          local noisy = CFG.NOISY[e.type]
          local gkey = noisy and table.concat({ e.type, e.att or "", e.def or "", tostring(e.kind or ""), tostring(e.by_player or ""),
                                                tostring(math.floor((e.day or 0) / CFG.MERGE_DAYS)) }, "|")
          if gkey and groups[gkey] then
            local g = groups[gkey].members
            g[#g + 1] = e.id                           -- V6: старшее однотипное событие той же пары — в группу свежего
          elseif not (noisy and not e.by_player and (R.noisyDay.n[e.type] or 0) >= noisy.cap) then
            local w = (noisy and not e.by_player) and noisy.weight or (CFG.BIG_SPEED_MULT[e.type] and CFG.BIG_WEIGHT) or 1
            if herald then w = w * CFG.HERALD_WEIGHT end
            local score = w / (1 + math.max(0, ageDays) / CFG.FRESH_DAYS) * (dist and 1 / (1 + dist / CFG.NEAR_SCALE) or 0.5)
            local c = { e = e, dist = dist, herald = herald, dir = (dist and direction(lx, lz, ex, ez)) or nil, ord = #cands, score = score,
                        members = { e.id } }
            cands[#cands + 1] = c
            if gkey then groups[gkey] = c end
          end
        end
      end
    end
    table.sort(cands, function(p, q)                 -- вес x свежесть x близость; тай-брейк — ближе, потом свежее
      if p.score ~= q.score then return p.score > q.score end
      local dp, dq = p.dist or 1e9, q.dist or 1e9
      if dp ~= dq then return dp < dq end
      return p.ord < q.ord
    end)
    for _, c in ipairs(cands) do
      local e, dist, dir = c.e, c.dist, c.dir
      local speaker = findSpeaker(listener)
      if not speaker then break end
      local level, _, role, rkind = roleOf(speaker)
      if dist and dist > CFG.FAR_DISTANCE then level = level + 1 end
      local text, kind, fkey = compose(e, level, dist, dir, #c.members, rkind, dayNow)
      if not text and kind == "forms_used" then   -- B1: все формы типа звучали за год — берём другое событие (или мелочь города)
        R.formSkip = R.formSkip or {}
        if not R.formSkip[e.id] then R.formSkip[e.id] = true; log("skip event=" .. tostring(e.id) .. " reason=forms_used type=" .. tostring(e.type)) end
      end
      if text then
        if c.herald then text = ((T[CFG.LANG] or T.en).herald or "") .. text end
        local okSay, errSay = pcall(function() speaker:say(text) end)
        local who = speakerName(speaker)
        if CFG.SHOW_IN_MESSAGE_LOG and rawget(_G, "ManagementScreen") then   -- прежний дубль строкой сверху (по умолчанию выкл.; журнал — V3)
          local L = T[CFG.LANG] or T.en
          local msg = L.msg:gsub("%%WHO%%", (tostring(who):gsub("%%", "%%%%"))):gsub("%%TEXT%%", (text:gsub("%%", "%%%%")))
          pcall(function() getGameWorld():showPlayerAMessage_withLog(msg, true) end)
        end
        local key = e.id .. "|" .. (okSay and "" or "!") .. tkey
        R.told[key] = true
        for i = 2, #c.members do R.told[c.members[i] .. "|=" .. tkey] = true end
        R.townCount[tkey] = (R.townCount[tkey] or 0) + 1
        R.lastTellClock = clk
        visit.told = visit.told + 1
        visit.spk[who] = (visit.spk[who] or 0) + 1
        R.spk.n[who] = (R.spk.n[who] or 0) + 1
        if CFG.NOISY[e.type] and not e.by_player then R.noisyDay.n[e.type] = (R.noisyDay.n[e.type] or 0) + 1 end
        local okF, f = pcall(io.open, CFG.TOLD_PATH, "a")
        if okF and f then f:write(key .. "\n"); f:close() end
        log(string.format("told event=%s town=%s speaker=%s role=%s level=%d dist=%s herald=%s kind=%s merged=%d score=%.3f form=%s say=%s text=%s",
          e.id, tkey, who, role, level, dist and string.format("%.0f", dist) or "?", tostring(c.herald), kind, #c.members - 1, c.score, tostring(fkey),
          okSay and "ok" or tostring(errSay), text))
        if #c.members > 1 then log(string.format("merge kind=%s n=%d event=%s", tostring(e.type), #c.members, e.id)) end
        if okSay then
          if fkey then R.forms[fkey] = dayNow end   -- B1: форма прозвучала — год не повторять
          journalAdd(e.id, who, cleanName(tkey, nil), text, dayI)   -- V3: услышанное остаётся в журнале
          mapHint(e, level, dist, now)   -- R2: наводка на карте (своя защита, ошибка выключает только карту)
        end
        told = told + 1
        if told >= CFG.MAX_PER_CHECK then break end
      end
    end
  end
  -- V4: в этом визите новостей не прозвучало — через ENTRY_DELAY_SEC после входа житель скажет о местном
  if told == 0 and CFG.SMALLTALK_ON and visit.told == 0 and not visit.small and clk - visit.t0 >= CFG.ENTRY_DELAY_SEC
     and (not R.smallHour[tkey] or now - R.smallHour[tkey] >= CFG.SMALLTALK_CD_HOURS or now < R.smallHour[tkey]) then
    local tsid = townSid(town)
    -- приветствие Nemesis в этом визите: уже сказал — мелочь не нужна; ещё может прозвучать — ждём. Нет модуля/функции — как раньше
    local gsaid, gpend = false, false
    local NM = rawget(_G, "KMM_Nemesis")
    if tsid and type(NM) == "table" and NM.greet_said then
      local okg, s1, s2 = pcall(NM.greet_said, tsid)
      if okg then gsaid, gpend = s1 == true, s2 == true end
    end
    if gsaid then
      visit.small = true
      log("smalltalk skip town=" .. tkey .. " reason=greet_said")
    elseif not gpend then
      local okT, said = pcall(smallTalk, listener, tkey, tsid, now, lx, lz)
      if not okT then log("smalltalk failed: " .. tostring(said)) end
      if not okT or said ~= nil then visit.small = true end
    end
  end
end

----------------------------------------------------------------------- ТИК
-- Числа из правил: KMM_Conductor.cfg().params.rumors = { KEY = значение } (ключи CFG верхнего уровня, тот же тип). Нет — DEF выше.
local function applyOverrides()
  if R.cfgApplied then return end
  local C = rawget(_G, "KMM_Conductor")
  if not (C and C.cfg) then return end
  R.cfgApplied = true
  local ok, ov = pcall(function() local c = C.cfg(); return c and c.params and c.params.rumors end)
  if not (ok and type(ov) == "table") then return end
  local n = 0
  for k, v in pairs(ov) do
    if CFG[k] ~= nil and type(CFG[k]) == type(v) and type(v) ~= "table" then CFG[k] = v; n = n + 1
    elseif CFG[k] ~= nil and type(v) == "table" and type(CFG[k]) == "table" then for k2, v2 in pairs(v) do CFG[k][k2] = v2 end; n = n + 1 end
  end
  log("config: " .. n .. " overrides from conductor params.rumors")
end
-- чистка R.told / R.heard (см. TOLD_KEEP_DAYS / TOLD_MAX). Источник не дирижёр или журнал пуст — не трогаем (нечем проверить)
local function pruneTold(dayNow)
  if R.src ~= "conductor" or #R.order == 0 then return 0 end
  local gone, old, cap = 0, 0, 0
  local function bad(id)
    local e = R.events[id]
    if not e then gone = gone + 1; return true end
    if dayNow and (e.day or 0) < dayNow - CFG.TOLD_KEEP_DAYS then old = old + 1; return true end
    return false
  end
  for k in pairs(R.told) do
    local id = tostring(k):match("^([^|]*)")
    if bad(id) then R.told[k] = nil end
  end
  for id in pairs(R.heard) do if bad(tostring(id)) then R.heard[id] = nil end end
  local keys = {}
  for k in pairs(R.told) do keys[#keys + 1] = { k = k, t = true, n = tonumber(tostring(k):match("^([^|]*)")) or 0 } end
  for k in pairs(R.heard) do keys[#keys + 1] = { k = k, t = false, n = tonumber(k) or 0 } end
  if #keys > CFG.TOLD_MAX then
    table.sort(keys, function(a, b) if a.n ~= b.n then return a.n < b.n end return tostring(a.k) < tostring(b.k) end)
    for i = 1, #keys - CFG.TOLD_MAX do
      if keys[i].t then R.told[keys[i].k] = nil else R.heard[keys[i].k] = nil end
      cap = cap + 1
    end
  end
  local n = gone + old + cap
  if n > 0 then log(string.format("told prune: removed=%d gone=%d old=%d cap=%d kept=%d", n, gone, old, cap, math.min(#keys, CFG.TOLD_MAX))) end
  return n
end
R.prune = pruneTold   -- офлайн-тест

local function resetWorld()
  R.told, R.townLastHour, R.heard, R.townCount, R.smallHour = {}, {}, {}, {}, {}
  R.visit, R.spk, R.noisyDay, R.smallLast, R.lastTellClock, R.visSig = nil, nil, nil, nil, nil, nil
  R.jq, R.jday, R.jdone, R.pruneDay = {}, { day = -1, n = 0 }, {}, nil
  R.forms, R.formSkip = {}, nil   -- B1: годовой учёт форм — свой у каждого мира
end

local function onTick()
  if h_live(R, "disabled", "KMM_Rumors.tick") then return end
  local t = os.clock()
  if t - R.lastCheck < CFG.CHECK_INTERVAL_SEC then return end
  R.lastCheck = t
  pcall(applyOverrides)
  local h = gameHours()
  if h and R.lastHours and h + 12 < R.lastHours then   -- время пошло назад: новая игра / другой мир
    resetWorld(); R.map.day = -1
    log(string.format("game time went back (%.1f < %.1f h) — told list reset", h, R.lastHours))
  end
  if h then R.lastHours = h end
  if R.disabled then return end
  if next(R.map.live) and not R.map.off and h then   -- R2: снять с карты отряды с истёкшим сроком
    local okE, errE = pcall(mapExpire, h)
    if not okE then mapOff("expire", errE) end
  end
  local ok, err = pcall(function()
    if not readConductor() then readChronicle() end
    local d = h and math.floor(h / 24)
    if d and R.pruneDay ~= d then R.pruneDay = d; pruneTold(h / 24); pruneForms(h / 24) end   -- раз в игровой день
    tryTell()
  end)
  if ok and t - (R.visT or -1e9) >= CFG.VIS_LOG_SEC then R.visT = t; pcall(visLog, false) end   -- B1: метрика видимости
  if not ok then
    local m = h_msg("tick", h_down(R, "disabled", "KMM_Rumors.tick", err), err)
    log(m)
    local okf, f = pcall(io.open, "C:/KenshiModMap/logs/debug.log", "a")
    if okf and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Rumors] ", m, "\n"); f:close() end
  else h_done("KMM_Rumors.tick") end
end

-- guard (как у остальных KMM-модулей): первая ошибка отключает только этот обработчик, причина → debug.log
local GUARD_OFF = {}
local function guarded(gname, fn)
  return function(...)
    if h_live(GUARD_OFF, gname, "KMM_Rumors." .. gname) then return end
    local ok, err = pcall(fn, ...)
    if not ok then
      local m = h_msg(gname, h_down(GUARD_OFF, gname, "KMM_Rumors." .. gname, err), err)
      log(m)
      local okf, f = pcall(io.open, "C:/KenshiModMap/logs/debug.log", "a")
      if okf and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Rumors] ", m, "\n"); f:close() end
    else h_done("KMM_Rumors." .. gname) end
  end
end

if R.tickHandler then pcall(Events.off, R.tickHandler) end   -- повторная загрузка скрипта не дублирует обработчик
R.disabled = nil
R.tickHandler = Events.on("GameWorld::charsUpdate", guarded("tick_hook", function(...)
  local ok, err = pcall(function(...) if _G.KMM_Gov then return KMM_Gov.run("rumors", onTick, ...) else return onTick(...) end end, ...)
  if not ok and not R.disabled then
    local m = h_msg("tick", h_down(R, "disabled", "KMM_Rumors.tick", err), err)
    log(m)
    local okf, f = pcall(io.open, "C:/KenshiModMap/logs/debug.log", "a")
    if okf and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Rumors] ", m, "\n"); f:close() end
  end
end))

-- Список рассказанного живёт в сейве мира (как журнал KMM_Conductor): новая игра = пустой список, загрузка = список этого сейва.
local TOLD_KEY = "kmm_rumors_told"
local FORMS_KEY = "kmm_rumors_forms"   -- B1: годовой учёт форм «тип#номер<TAB>день»; необязательное поле: старый сейв без него = пустой учёт
if R.saveHandler then pcall(Events.off, R.saveHandler) end
if R.loadHandler then pcall(Events.off, R.loadHandler) end
function R.save_ids()
  local ids = {}
  pcall(function()
    local sm = SaveManager and SaveManager.getSingleton and SaveManager.getSingleton()
    if not sm then return end
    for _, key in ipairs({ "name", "currentGame" }) do
      local okv, v = pcall(function() return sm[key] end)
      if okv and type(v) == "string" and v ~= "" then
        local id = v:gsub("[^%w%-_ ]", "_")
        if not ids[id] then ids[#ids + 1] = id; ids[id] = true end
      end
    end
  end)
  return ids
end
R.saveHandler = Events.on("PlayerInterface::serialise", guarded("save", function(_, gd)
  pcall(function() local h = gameHours(); pruneTold(h and h / 24) end)   -- в сейв — только нужное
  local keys = {}
  for k in pairs(R.told) do keys[#keys + 1] = k end
  for id in pairs(R.heard) do keys[#keys + 1] = "@" .. tostring(id) end   -- NEWS: старый код прочтёт это как безвредный ключ told
  local str = table.concat(keys, "\n")
  local ok, err = pcall(function() gd.sdata[TOLD_KEY] = str end)
  if not ok then log("serialise told list failed: " .. tostring(err)) end
  pcall(visLog, true)   -- B1: метрика видимости на каждом сохранении
  pcall(function() local h = gameHours(); pruneForms(h and h / 24) end)
  local fl = {}
  for k, d in pairs(R.forms) do if type(d) == "number" then fl[#fl + 1] = k .. "\t" .. string.format("%.2f", d) end end
  table.sort(fl)
  local fstr = table.concat(fl, "\n")
  local okF, errF = pcall(function() gd.sdata[FORMS_KEY] = fstr end)
  if not okF then log("serialise forms failed: " .. tostring(errF)) end
  for _, id in ipairs(R.save_ids()) do   -- PERSIST 2026-11-13: запасная копия (загрузка sdata в игре вернула пусто)
    local okf, f = pcall(io.open, "C:/KenshiModMap/state/" .. id .. ".rumors", "w")
    if okf and f then pcall(function() f:write(str) end); f:close() end
    local okg, g = pcall(io.open, "C:/KenshiModMap/state/" .. id .. ".rumorforms", "w")
    if okg and g then pcall(function() g:write(fstr) end); g:close() end
  end
end))
R.loadHandler = Events.on("PlayerInterface::loadFromSerialise", guarded("load", function(_, gd)
  resetWorld(); R.lastHours = nil
  local ok, v = pcall(function() return gd.sdata[TOLD_KEY] end)
  local how = "index"
  if not (ok and type(v) == "string" and v ~= "") then
    local okt, t = pcall(function() return gd.sdata:toTable() end)
    if okt and type(t) == "table" and type(t[TOLD_KEY]) == "string" then ok, v, how = true, t[TOLD_KEY], "toTable" end
  end
  if not (ok and type(v) == "string" and v ~= "") then
    for _, id in ipairs(R.save_ids()) do
      local okf, f = pcall(io.open, "C:/KenshiModMap/state/" .. id .. ".rumors", "r")
      if okf and f then
        local okr, fs = pcall(function() return f:read("*a") end); f:close()
        if okr and type(fs) == "string" then ok, v, how = true, fs, "file:" .. id; break end
      end
    end
  end
  local n = 0
  if ok and type(v) == "string" then
    for k in v:gmatch("[^\n]+") do
      if k:sub(1, 1) == "@" then R.heard[k:sub(2)] = true else R.told[k] = true; n = n + 1 end
    end
  end
  log("told list loaded from save: " .. n .. " via " .. how)
  -- B1: учёт форм (нет поля — старый сейв: пусто)
  local okv, fv = pcall(function() return gd.sdata[FORMS_KEY] end)
  local fhow = "index"
  if not (okv and type(fv) == "string" and fv ~= "") then
    local okt, t = pcall(function() return gd.sdata:toTable() end)
    if okt and type(t) == "table" and type(t[FORMS_KEY]) == "string" then okv, fv, fhow = true, t[FORMS_KEY], "toTable" end
  end
  if not (okv and type(fv) == "string" and fv ~= "") and how:sub(1, 5) == "file:" then   -- сейв читался из файла — и формы оттуда
    local okf, f = pcall(io.open, "C:/KenshiModMap/state/" .. how:sub(6) .. ".rumorforms", "r")
    if okf and f then local okr, fs = pcall(function() return f:read("*a") end); f:close(); if okr and type(fs) == "string" then okv, fv, fhow = true, fs, how end end
  end
  local nf = 0
  if okv and type(fv) == "string" then
    for k, d in fv:gmatch("([^\t\n]+)\t([%d%.%-]+)") do
      local dn = tonumber(d)
      if dn then R.forms[k] = dn; nf = nf + 1 end
    end
  end
  log("forms ledger loaded from save: " .. nf .. " via " .. fhow)
end))

-- Отладка из консоли KenshiLua (Ctrl+Shift+L):
--   KMM_Rumors.test("text")   — ближайший NPC в городе скажет текст
--   KMM_Rumors.status()       — сколько событий знаем и рассказали
R.test = function(text)
  local listener = playerInTown()
  if not listener then return "player not in a town" end
  local s = findSpeaker(listener)
  if not s then return "no NPC within " .. CFG.TALK_RADIUS end
  local ok, err = pcall(function() s:say(text or "Testing rumours.") end)
  pcall(function() getGameWorld():showPlayerAMessage_withLog("KMM_Rumors test: " .. tostring(text), true) end)
  return ok and ("said by " .. tostring(s:getName())) or tostring(err)
end
R.status = function()
  local n = 0
  for _ in pairs(toldIndex()) do n = n + 1 end
  return string.format("events=%d told=%d towns=%d map_places=%d map_squads=%d map_off=%s", #R.order, n, (function() local k = 0 for _ in pairs(TOWNS) do k = k + 1 end return k end)(),
    R.map.places, R.map.squads, tostring(R.map.off == true))
end
R.CFG = CFG

R.news = { townXZ = townXZ, eventXZ = eventXZ, delay = newsDelay, heralds = scanHeralds }
R.mapfn = { hint = mapHint, expire = mapExpire, find = findPlace, outlaw = findOutlaw }   -- R2: офлайн-тест
R.fn = { tellable = tellable, compose = compose, small = smallLines, told = toldIndex, journal = journalFlush, vislog = visLog }   -- B1: офлайн-тест
R.T = T   -- тексты (только читать; офлайн-тест форм)
log("loaded v1: chronicle=" .. CFG.CHRONICLE_PATH .. " news_speed=" .. CFG.NEWS_SPEED .. " max_days=" .. CFG.NEWS_MAX_DAYS .. " lang=" .. CFG.LANG .. " map=" .. tostring(CFG.MAP.ON) .. " map_places_day=" .. CFG.MAP.MAX_PLACES_DAY ..
  " town_window_h=" .. CFG.TOWN_COOLDOWN_HOURS .. " per_town=" .. CFG.MAX_PER_TOWN .. " journal=" .. tostring(CFG.JOURNAL_ON) .. " smalltalk=" .. tostring(CFG.SMALLTALK_ON))
