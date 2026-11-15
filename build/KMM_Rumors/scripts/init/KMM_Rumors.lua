-- KMM_Rumors v0 — слухи из хроники дирижёра (поток B RUMORS).
-- Источник: C:\KenshiModMap\logs\chronicle.log (контракт потока A, TSV):
--   game_day, event_id, event_type, town_sid, town_name, faction_attacker, faction_defender,
--   leader_sid, leader_name, status, text
-- Доставка (то, что подтверждено рабочими примерами CK/Bloodlines или биндингами — см. docs/streams/RUMORS.md):
--   * реплика NPC рядом с игроком: Character:say(text)              [подтверждено: CKBloodlines.lua]
--   * дубль в журнал сообщений:    GameWorld:showPlayerAMessage_withLog(text, queued)   [по биндингам, не проверено]
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
  CHECK_INTERVAL_SEC   = 60,       -- как часто (реальные секунды) проверять, есть ли кому рассказать
  TALK_RADIUS          = 900,      -- рассказчик должен быть ближе стольких единиц к персонажу игрока
  TOWN_COOLDOWN_HOURS  = 48,       -- не чаще одного слуха на город за столько игровых часов
  MAX_PER_CHECK        = 1,        -- слухов за одну проверку
  SHOW_IN_MESSAGE_LOG  = false,    -- дублировать в журнал сообщений игрока
  WRONG_OUTCOME_CHANCE = 0.3,      -- уровень искажения 2: шанс перепутать исход (убит <-> пленён / отбились <-> пал)
  -- роль рассказчика по имени шаблона (data.name), первое совпадение; уровень: 0 точно, 1 без имён, 2 преувеличивает/путает
  ROLES = {
    { match = { "barman", "bartender", "bar keeper", "innkeeper" }, level = 0, prefer = 3 },
    { match = { "trader", "merchant", "caravan", "shop" },           level = 0, prefer = 2 },
    { match = { "guard", "samurai", "soldier", "police", "paladin" }, level = 1, prefer = 1 },
    { match = { "bandit", "thug", "drifter", "vagrant", "beggar", "slave" }, level = 2, prefer = 1 },
  },
  DEFAULT_LEVEL        = 1,
}

local TAG = "[KMM_Rumors] "

----------------------------------------------------------------------- ТЕКСТЫ
local T = {
  en = {
    leader_killed   = { "Word is %LEADER% was killed at %TOWN%. %ATT% did it.", "They say %LEADER% is dead — %ATT% hit %TOWN%." },
    leader_captured = { "Heard %ATT% took %LEADER% alive at %TOWN%.", "Rumour has it %LEADER% is in %ATT% chains now." },
    attack_repelled = { "%ATT% went for %TOWN%, but %DEF% threw them back.", "Fighting at %TOWN%. %DEF% held." },
    raid            = { "%ATT% raided %DEF% — carts of loot went past here.", "Heard %DEF% got hit by %ATT% again." },
    town_captured   = { "%TOWN% belongs to %ATT% now. %DEF% lost it.", "They say %ATT% flew their colours over %TOWN%." },
    mobilized       = { "%ATT% are on the march. Big warbands, out in the open.", "Something stirred %ATT%. They're mustering." },
    demobilized     = { "%ATT% went quiet again. Back to their own business.", "Whatever riled %ATT% is over, it seems." },
    treaty_signed   = { "%ATT% and %DEF% made a deal.", "Word is %ATT% and %DEF% shook hands. Watch out." },
    treaty_broken   = { "%ATT% and %DEF% are done with each other.", "That pact between %ATT% and %DEF%? Gone." },
    betrayal        = { "%ATT% stabbed %DEF% in the back. Nobody will trust them now.", "%DEF% trusted %ATT%. Big mistake." },
    ally_help       = { "%ATT% came to help %DEF%. Kept their word.", "%ATT% sent fighters to back %DEF%." },
    ally_failed     = { "%DEF% called for help and %ATT% never came.", "%ATT% left %DEF% to hang." },
    faction_fell    = { "%ATT% are finished. Scattered to the winds.", "Nobody's seen %ATT% in a while. They're done." },
    faction_rise    = { "%ATT% are getting strong. More towns every season.", "Mark my words, %ATT% will rule half the map." },
    faction_decline = { "%ATT% are losing ground.", "Things look bad for %ATT%. Town after town lost." },
    revolt          = { "%TOWN% rose up against %DEF%.", "Heard the people of %TOWN% threw %DEF% out." },
    town_rejoined   = { "%TOWN% went back to %ATT%. Quietly, they say.", "%ATT% have %TOWN% again — no fighting." },
    mine_exhausted  = { "The seams at %TOWN% are dead. Miners just walked off.", "Nothing left to dig at %TOWN%." },
    mine_opened     = { "%ATT% sank a deep mine at %TOWN%. Iron's worth the risk now.", "%ATT% are digging deep near %TOWN%." },
    ore_crisis      = { "Iron's scarce everywhere. Smiths are melting down old blades.", "Metal prices keep climbing. Every caravan with ore gets hit." },
    story_scramble  = { "More and more people are digging in the old ruins. Something is out there, they say." },
    story_famine    = { "Iron is the only thing anyone talks about now. Hunger for metal." },
    story_twilight  = { "The old war-gear is failing. The ones who wore it are nervous." },
    story_night     = { "The dark gods whisper louder every month. Even the guards pray." },
    story_forge     = { "Smiths say the ancient craft can be learned again. Slowly, at a price." },
    story_ashes     = { "The old powers are ash. Whoever is left is building something new." },
    elite_hunger    = { "%ATT% can't mend their wonders anymore. Their patrols look desperate.", "Even %ATT% are running out of the old parts." },
    ruin_expedition = { "%ATT% went digging in %TOWN%. Came back with scrap.", "Saw %ATT% hauling junk out of %TOWN%." },
    famine          = { "Hunger in %TOWN%. Families on the roads.", "%ATT% can't feed their people. Bread lines at %TOWN%." },
    theft           = { "Thieves of %ATT% cleaned out %DEF% storehouses.", "Stolen goods everywhere — %ATT% work, they say." },
    drug_bust       = { "%ATT% caught smugglers of %DEF% with a load of hash.", "%ATT% burned a hashish cargo. %DEF% won't like it." },
    slave_raid      = { "%ATT% hunters took people of %DEF% in chains.", "Another slave column from %DEF% lands. %ATT% again." },
    black_market    = { "%ATT% unloaded a cargo at %TOWN% you don't ask about. %DEF% paid, no questions.", "Busy night at %TOWN%: %ATT% selling, %DEF% buying. Don't ask what.", "Word is %DEF% buy from %ATT% at %TOWN%. Everyone knows, nobody says." },
    slaves_freed    = { "%ATT% struck a %DEF% slave column. Set them all free.", "Heard %ATT% freed slaves of %DEF%." },
    succession_crisis = { "%ATT% are fighting over who leads them now.", "No one rules %ATT%. Knives are out." },
    succession_resolved = { "%ATT% have a new master.", "The squabbling in %ATT% is over. New boss." },
    faction_split   = { "%ATT% broke away from %DEF%.", "%DEF% split — %ATT% walk their own road now." },
    warlord_rose    = { "A warlord gathers men — %ATT%, they call themselves.", "Some warlord's rallying the angry ones of %DEF%." },
    chaos_cult      = { "Strange cultists in %TOWN%. Whispering about dark gods.", "Something foul grows in %TOWN%. People vanish at night." },
    base_raid       = { "%ATT% are talking about that new settlement. They want what's there.", "%ATT% plan to hit the Nameless settlement." },
    base_campaign   = { "%ATT% are talking about that new settlement. They want what's there.", "%ATT% plan to hit the Nameless settlement." },   -- U2: рейд-кампания движка
    recruit_merc_hired   = { "%LEADER% of %ATT% hired %DEF% blades near %TOWN%. Strike when the contract runs out.", "%ATT% paid %DEF% to guard %LEADER%. Two days, they say." },   -- X2
    recruit_merc_left    = { "The %DEF% blades left %LEADER% of %ATT%. Contract's over.", "%LEADER% walks without guards again. %DEF% went home." },
    recruit_slave_bought = { "%ATT% bought the strongest slave in %TOWN%: %LEADER%. Nobody else got a chance.", "The best one in the %TOWN% cages, %LEADER%? %ATT% took him first." },
    recruit_slave_freed  = { "%LEADER%, bought by %ATT%, walks free. Someone broke the chains.", "Heard %LEADER% slipped the %ATT% chains. Somebody helped." },
    ally_joins      = { "%ATT% marched out against %DEF%, beside some drifters.", "%ATT% joined a fight against %DEF%." },
    relic_salvage   = { "%ATT% dragged something ancient out of the ruins. Still humming.", "They say %ATT% found a vault of the old ones." },
    elite_seen      = { "%ATT% sent out their elite near %TOWN%. Heavy armour, cold eyes.", "Saw an honour guard of %ATT% by %TOWN%. Steer clear." },
    stock_shortage  = { "%TOWN% is running out of %CAT%. Prices are climbing.", "Can't find %CAT% in %TOWN% for love or money." },
    stock_glut      = { "%TOWN% is drowning in %CAT%. Traders sell it for nothing.", "Too much %CAT% in %TOWN%. Good time to buy." },
    stock_sacked    = { "%ATT% stripped %TOWN% bare. Stores, shelves, everything.", "%TOWN%'s warehouses were looted by %ATT%." },
    town_shortage   = { "The smiths of %TOWN% stand idle. No %CAT% to work with.", "Workshops in %TOWN% are short on %CAT%." },
    smuggle_run     = { "Smugglers got a load of %CAT% into %TOWN% past the guards. Pricey, but it's there.", "Somebody ran %CAT% into %TOWN% in the night. Ask no questions." },
    contraband_caught = { "%ATT% guards nabbed a drifter selling %CAT% in %TOWN%. They're furious.", "A Nameless trader was caught peddling %CAT% in %TOWN%. %ATT% won't forget it." },
    gear_worn       = { "The patrols of %ATT% walk about in rusted armour. Their armouries must be empty.", "%ATT% soldiers wear patched, rusty kit these days. Hard times for them." },
    player_sold     = { "Some drifter has been selling goods in %TOWN%. %CAT% prices are falling.", "A Nameless trader unloaded a lot of %CAT% in %TOWN%." },
    caravan_lost    = { "A %ATT% caravan never arrived. Wolves, bandits, who knows.", "%ATT% lost a trade caravan on the road. Bodies by the track." },
    refugees        = { "Refugees from %TOWN% are on the roads. Hungry ones.", "Whole families left %TOWN% with what they could carry." },
    relic_forge_known = { "They say the Nameless built a thinking machine of the ancients.", "Rumour has it some drifters assembled a machine mind. Fools or geniuses." },
    trade_for       = { "%ATT% are buying up %CAT% from %DEF%, whatever the price.", "Caravans of %ATT% carry %CAT% from %DEF%. Paid in full." },
    raid_surplus    = { "%ATT% came back from %TOWN% loaded with %CAT%.", "After the raid on %TOWN%, %ATT% have more %CAT% than they can store." },
    waylay          = { "%ATT% are robbing the travellers of %DEF% on the roads. Take an escort.", "Caravans of %DEF% keep vanishing; people whisper that %ATT% are waiting in the hills." },
    loot_sold       = { "Somebody is selling plundered goods in %TOWN%. %CAT%, cheap, no questions asked.", "In %TOWN% they say %ATT% unload their loot on the market. Mostly %CAT%." },
    cats = { food = "food", metal = "metal", weapons = "weapons", armor = "armour", med = "medicine", drugs = "drugs", lux = "luxuries", scrap = "scrap", goods = "goods" },
    chaos_incursion = { "Something tore the sky open near %TOWN%. Things with horns came out.", "Daemons near %TOWN%. I'm not joking." },
    some_leader = "some big shot", some_faction = "someone", far = "somewhere far to the %DIR%",
    dirs = { n = "north", s = "south", e = "east", w = "west" },
    hedge = { " Or so they say.", " Don't quote me.", "" },
    herald = "Newcomers off the road say: ",
    msg = "Rumour (%WHO%): %TEXT%",
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
    story_scramble  = { "В старых руинах копаются всё чаще. Говорят, там что-то есть." },
    story_famine    = { "Теперь все говорят только о железе. Голод по металлу." },
    story_twilight  = { "Древнее снаряжение отказывает. Те, кто его носил, нервничают." },
    story_night     = { "Тёмные боги шепчут всё громче. Даже стража молится." },
    story_forge     = { "Кузнецы говорят: древнему ремеслу можно научиться заново. Медленно и дорого." },
    story_ashes     = { "Старые силы обратились в пепел. Те, кто остался, строят новое." },
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
  },
}

----------------------------------------------------------------------- СОСТОЯНИЕ
_G.KMM_Rumors = _G.KMM_Rumors or {}
local R = _G.KMM_Rumors
R.events = R.events or {}          -- event_id -> событие (последняя строка с этим id)
R.order = R.order or {}            -- порядок event_id
R.told = R.told or {}              -- "event_id|town" -> true
R.townLastHour = R.townLastHour or {}
R.fileSize = R.fileSize or -1
R.lastCheck = R.lastCheck or 0

local okTowns, TOWNS = pcall(require, "kmm_rumors_towns")
if not okTowns or type(TOWNS) ~= "table" then TOWNS = {}; print(TAG .. "town table not loaded: " .. tostring(TOWNS)) end

local function log(line)
  local ok, f = pcall(io.open, CFG.LOG_PATH, "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S") .. "\t" .. line .. "\n"); f:close() end
  print(TAG .. line)
end

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
                   x = tonumber(ev.x), z = tonumber(ev.z) }   -- R2: точка события (место боя и т.п.) для метки на карте
    order[#order + 1] = id
   end
  end
  R.events, R.order = events, order
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
      if name:find(m, 1, true) then return r.level, r.prefer, name end
    end
  end
  return CFG.DEFAULT_LEVEL, 0, name
end

local function direction(fromX, fromZ, toX, toZ)
  local dx, dz = toX - fromX, toZ - fromZ
  if math.abs(dx) > math.abs(dz) then return dx > 0 and "e" or "w" end
  return dz > 0 and "s" or "n"   -- в Kenshi север — отрицательный z (не проверено; при ошибке поменять местами)
end

local function compose(e, level, dist, dir)
  local L = T[CFG.LANG] or T.en
  local kind = e.type
  if level >= 2 and math.random() < CFG.WRONG_OUTCOME_CHANCE then
    local swap = { leader_killed = "leader_captured", leader_captured = "leader_killed", attack_repelled = "leader_killed",
                   treaty_signed = "betrayal", treaty_broken = "betrayal", mobilized = "raid", ally_help = "ally_failed", faction_decline = "faction_fell" }
    kind = swap[kind] or kind
  end
  local pool = L[kind]
  if not pool then   -- ЖИВОЙ МИР (2026-11-13): типы внешних модулей без шаблона — готовый текст события (en), с оговоркой по дальности
    local pfx = { "fate_", "relic_", "predator_", "siege_", "herd", "veteran", "bounty_hunters", "slave_caravan", "famine_refugees", "outlaw_", "nemesis_", "debt_", "deed", "base_raid_", "recruit_" }   -- deed: дела мира из KMM_Deeds (ядро affectRelations)
    local ok_t = false
    for _, p in ipairs(pfx) do if kind:sub(1, #p) == p then ok_t = true; break end end
    if not (ok_t and e.text and e.text ~= "") then return nil end
    local s0 = e.text
    if level >= 1 and L.hedge then s0 = s0 .. L.hedge[math.random(#L.hedge)] end
    return s0, kind
  end
  local s = pool[math.random(#pool)]
  local leader = (level >= 1 or e.leader == "") and L.some_leader or e.leader
  local town = (e.town ~= "" and e.town) or "?"
  if (level >= 2 or (dist and dist > CFG.FAR_DISTANCE)) and dir then town = L.far:gsub("%%DIR%%", L.dirs[dir]) end
  local att = (e.att ~= "" and e.att) or L.some_faction
  local def = (e.def ~= "" and e.def) or L.some_faction
  if level >= 2 and math.random() < 0.5 then if math.random() < 0.5 then att = L.some_faction else def = L.some_faction end end   -- путает, кто это был
  local function esc(x) return (tostring(x):gsub("%%", "%%%%")) end   -- % в подстановке gsub
  s = s:gsub("%%LEADER%%", esc(leader)):gsub("%%TOWN%%", esc(town)):gsub("%%ATT%%", esc(att)):gsub("%%DEF%%", esc(def))
  local cats = L.cats or {}
  s = s:gsub("%%CAT%%", esc(cats[e.cat or ""] or cats.goods or "goods"))
  if level >= 1 then s = s .. L.hedge[math.random(#L.hedge)] end
  return s, kind
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
        if alive then
          local level, prefer = roleOf(r.ch)
          local score = prefer * 10000 - d
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
      local level, prefer = roleOf(c)
      local score = prefer * 10000 - d
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
  R.map.off = true
  log("map disabled until restart in " .. where .. ": " .. tostring(err))
  local okf, f = pcall(io.open, "C:/KenshiModMap/logs/debug.log", "a")
  if okf and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Rumors] map disabled until restart in ", where, ": ", tostring(err), "\n"); f:close() end
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
  if not CFG.MAP.ON or R.map.off then return end
  local d = math.floor(now / 24)
  if d ~= R.map.day then R.map.day, R.map.places, R.map.squads = d, 0, 0 end
  if level >= 2 or (dist and dist > CFG.FAR_DISTANCE) then log("map skip event=" .. tostring(e.id) .. " reason=vague level=" .. level); return end
  local ok, err = pcall(mapPlace, e)
  if not ok then mapOff("place", err); return end
  ok, err = pcall(mapSquad, e, now)
  if not ok then mapOff("squad", err) end
end

local function tryTell()
  local now = gameHours()
  if not now then return end
  local listener, town = playerInTown()
  if not listener then return end
  local tkey = townKey(town)
  if R.townLastHour[tkey] and now - R.townLastHour[tkey] < CFG.TOWN_COOLDOWN_HOURS then return end
  local lx, lz = vec(listener:getPosition())
  pcall(scanHeralds, lx, lz)
  local told = 0
  local cands = {}
  local dayNow = now / 24
  for i = #R.order, 1, -1 do                       -- свежие события первыми
    local e = R.events[R.order[i]]
    local key = e.id .. "|" .. tkey
    if not R.told[key] then
      local ex, ez = eventXZ(e)
      local delay, dist = newsDelay(e, ex, ez, lx, lz)
      local herald = R.heard[e.id] and true or false
      if herald then delay = 0 end
      local ageDays = dayNow - e.day
      if ageDays >= delay and ageDays <= CFG.MAX_AGE_DAYS then
        cands[#cands + 1] = { e = e, key = key, dist = dist, herald = herald, dir = (dist and direction(lx, lz, ex, ez)) or nil, ord = #cands }
      end
    end
  end
  table.sort(cands, function(p, q)                 -- сначала ближние (вести доходят раньше), потом свежие
    local dp, dq = p.dist or 1e9, q.dist or 1e9
    if dp ~= dq then return dp < dq end
    return p.ord < q.ord
  end)
  for _, c in ipairs(cands) do
    local e, key, dist, dir = c.e, c.key, c.dist, c.dir
    local speaker = findSpeaker(listener)
    if not speaker then return end
    local level, _, role = roleOf(speaker)
    if dist and dist > CFG.FAR_DISTANCE then level = level + 1 end
    local text, kind = compose(e, level, dist, dir)
    if text then
      if c.herald then text = ((T[CFG.LANG] or T.en).herald or "") .. text end
      local okSay, errSay = pcall(function() speaker:say(text) end)
      local who = "?"
      pcall(function() who = speaker:getName() end)
      if CFG.SHOW_IN_MESSAGE_LOG then
        local L = T[CFG.LANG] or T.en
        local msg = L.msg:gsub("%%WHO%%", (tostring(who):gsub("%%", "%%%%"))):gsub("%%TEXT%%", (text:gsub("%%", "%%%%")))
        pcall(function() getGameWorld():showPlayerAMessage_withLog(msg, true) end)
      end
      R.told[key] = true
      R.townLastHour[tkey] = now
      local okF, f = pcall(io.open, CFG.TOLD_PATH, "a")
      if okF and f then f:write(key .. "\n"); f:close() end
      log(string.format("told event=%s town=%s speaker=%s role=%s level=%d dist=%s herald=%s kind=%s say=%s text=%s",
        e.id, tkey, who, role, level, dist and string.format("%.0f", dist) or "?", tostring(c.herald), kind, okSay and "ok" or tostring(errSay), text))
      if okSay then mapHint(e, level, dist, now) end   -- R2: наводка на карте (своя защита, ошибка выключает только карту)
      told = told + 1
      if told >= CFG.MAX_PER_CHECK then return end
    end
  end
end

----------------------------------------------------------------------- ТИК
local function onTick()
  if R.disabled then return end
  local t = os.clock()
  if t - R.lastCheck < CFG.CHECK_INTERVAL_SEC then return end
  R.lastCheck = t
  local h = gameHours()
  if h and R.lastHours and h + 12 < R.lastHours then   -- время пошло назад: новая игра / другой мир
    R.told, R.townLastHour, R.heard = {}, {}, {}; R.map.day = -1
    log(string.format("game time went back (%.1f < %.1f h) — told list reset", h, R.lastHours))
  end
  if h then R.lastHours = h end
  if R.disabled then return end
  if next(R.map.live) and not R.map.off and h then   -- R2: снять с карты отряды с истёкшим сроком
    local okE, errE = pcall(mapExpire, h)
    if not okE then mapOff("expire", errE) end
  end
  local ok, err = pcall(function() if not readConductor() then readChronicle() end; tryTell() end)
  if not ok then
    R.disabled = true
    log("tick disabled until restart: " .. tostring(err))
    local okf, f = pcall(io.open, "C:/KenshiModMap/logs/debug.log", "a")
    if okf and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Rumors] tick disabled until restart: ", tostring(err), "\n"); f:close() end
  end
end

-- guard (как у остальных KMM-модулей): первая ошибка отключает только этот обработчик, причина → debug.log
local GUARD_OFF = {}
local function guarded(gname, fn)
  return function(...)
    if GUARD_OFF[gname] then return end
    local ok, err = pcall(fn, ...)
    if not ok then
      GUARD_OFF[gname] = true
      log(gname .. " disabled until restart: " .. tostring(err))
      local okf, f = pcall(io.open, "C:/KenshiModMap/logs/debug.log", "a")
      if okf and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Rumors] ", gname, " disabled until restart: ", tostring(err), "\n"); f:close() end
    end
  end
end

if R.tickHandler then pcall(Events.off, R.tickHandler) end   -- повторная загрузка скрипта не дублирует обработчик
R.disabled = nil
R.tickHandler = Events.on("GameWorld::charsUpdate", guarded("tick_hook", function(...)
  local ok, err = pcall(function(...) if _G.KMM_Gov then return KMM_Gov.run("rumors", onTick, ...) else return onTick(...) end end, ...)
  if not ok and not R.disabled then
    R.disabled = true
    log("tick disabled until restart: " .. tostring(err))
    local okf, f = pcall(io.open, "C:/KenshiModMap/logs/debug.log", "a")
    if okf and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " [KMM_Rumors] tick disabled until restart: ", tostring(err), "\n"); f:close() end
  end
end))

-- Список рассказанного живёт в сейве мира (как журнал KMM_Conductor): новая игра = пустой список, загрузка = список этого сейва.
local TOLD_KEY = "kmm_rumors_told"
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
  local keys = {}
  for k in pairs(R.told) do keys[#keys + 1] = k end
  for id in pairs(R.heard) do keys[#keys + 1] = "@" .. tostring(id) end   -- NEWS: старый код прочтёт это как безвредный ключ told
  local str = table.concat(keys, "\n")
  local ok, err = pcall(function() gd.sdata[TOLD_KEY] = str end)
  if not ok then log("serialise told list failed: " .. tostring(err)) end
  for _, id in ipairs(R.save_ids()) do   -- PERSIST 2026-11-13: запасная копия (загрузка sdata в игре вернула пусто)
    local okf, f = pcall(io.open, "C:/KenshiModMap/state/" .. id .. ".rumors", "w")
    if okf and f then pcall(function() f:write(str) end); f:close() end
  end
end))
R.loadHandler = Events.on("PlayerInterface::loadFromSerialise", guarded("load", function(_, gd)
  R.told, R.townLastHour, R.lastHours, R.heard = {}, {}, nil, {}
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
  for _ in pairs(R.told) do n = n + 1 end
  return string.format("events=%d told=%d towns=%d map_places=%d map_squads=%d map_off=%s", #R.order, n, (function() local k = 0 for _ in pairs(TOWNS) do k = k + 1 end return k end)(),
    R.map.places, R.map.squads, tostring(R.map.off == true))
end
R.CFG = CFG

R.news = { townXZ = townXZ, eventXZ = eventXZ, delay = newsDelay, heralds = scanHeralds }
R.mapfn = { hint = mapHint, expire = mapExpire, find = findPlace, outlaw = findOutlaw }   -- R2: офлайн-тест
log("loaded v0: chronicle=" .. CFG.CHRONICLE_PATH .. " news_speed=" .. CFG.NEWS_SPEED .. " max_days=" .. CFG.NEWS_MAX_DAYS .. " lang=" .. CFG.LANG .. " map=" .. tostring(CFG.MAP.ON) .. " map_places_day=" .. CFG.MAP.MAX_PLACES_DAY)
