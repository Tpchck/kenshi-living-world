-- KMM_Nemesis — память мира об игроке (2026-11-14, «живая искра»). Кого игрок избил и оставил живым (или кто сбежал из боя),
-- тот может вернуться: с прозвищем, которое дала эта встреча, растущей бандой и личной обидой — он идёт за игроком из региона
-- в регион. За убитого вожака может поклясться мститель. При встрече главарь говорит игроку реплику о месте и деле (Character:say).
-- Кого игрок снова уложит и снова оставит жить — растёт («Twice-Spared»); убитый окончательно — слух «Безымянные добили …».
-- Устройство: поверх KMM_Outlaws (имена, родная награда ядра, спавн у игрока через KMM_Traces, гибель/тюрьма/слухи уже там).
-- Здесь только: учёт ударов игрока (хук дирижёра Character::_NV_hitByMeleeAttack -> KMM_Nemesis.on_player_hit), исход боя
-- (isDead / isDown через pcall), рождение соперника (запись разыскиваемого с полем pg), преследование, реплики, события.
-- Состояние: S.ext.nemesis + поле pg у записи разыскиваемого (сейв дирижёра). Лог: C:/KenshiModMap/logs/nemesis.log.
-- Всё под pcall; ошибка -> модуль выключается до перезапуска. Kenshi Lua 5.1; всё — поля таблицы N (лимит локалей).
local TAG = "[KMM_Nemesis] "
local N = { off = false, cand = {}, last = -1000, nlog = 0, said = {} }

N.DEF = {
  enabled = true,
  tick_s = 3,
  linger_s = 75,          -- столько секунд без новых ударов игрока = бой с этим NPC окончен
  near_r = 5000,          -- ближе — персонаж загружен, можно спрашивать isDead/isDown
  max_wait_s = 900,       -- лежачего ждём не дольше (встал / игрок ушёл / добит)
  min_hits = 2,
  rival_p_spared = 0.35,  -- уложен игроком и оставлен жить
  rival_p_fled = 0.12,    -- ушёл из боя на ногах (игрок при этом не ложился)
  rival_p_beat = 0.25,    -- ОБРАТНАЯ ПАМЯТЬ: персонаж игрока лёг, победитель (ванильное Character.lastGuyWhoDefeatedMe) стоял — запомнил игрока
  beat_win_r = 2500,      -- победитель жив и не дальше от уложенного персонажа игрока (поле хранит последнего победителя)
  beat_scan_s = 3,        -- опрос «свой встал/лёг» не чаще
  weak_max_rivals = 1,    -- игрок нищ и слаб (N.worth): живых соперников не больше (спираль поражений)
  weak_rival_mult = 0.5,  -- и шанс нового соперника x
  avenger_p = 0.3,        -- убит вожак/именной -> мститель
  leader_mult = 2.0,
  max_rivals = 4,         -- живых соперников одновременно
  cooldown_days = 3,      -- не чаще одного нового соперника в N дней
  follow_p = 0.5,         -- в игровой день соперник перебирается в регион игрока
  grow_days = 12,         -- каждые N дней соперник растёт на тир (до 3)
  bounty_day = 120,
  say_delay_s = 6,
  log_max = 1000,          -- реплики, горожане, события за длинную сессию; маркеры отчёта сессии не должны вытесняться
  -- ДОЛЖНИКИ: кого игрок вылечил (≥ heal_need с первой помощи) или освободил из оков — возвращают долг
  debts = true,
  heal_need = 20,          -- секунд лечения чужого (CharStats::xpFirstAid, time — доли секунды за вызов)
  lockpick_window = 25,    -- оковы снялись в эти секунды после удачного взлома игроком = освободил он
  max_debts = 8,
  help_cd_days = 4,        -- не чаще одной помощи в N дней
  help_min_days = 1,       -- долг созревает
  word_days = 18,          -- не случилось боя — должник разносит добрую молву (отношение его фракции к игроку)
  word_rel = 6,
  -- ИМЕННЫЕ ОХОТНИКИ: у каждой правоохранительной фракции свой охотник за головой игрока; возвращается с новой охотой,
  -- помнит, где его побили (и приходит сильнее), убит — контракт берёт преемник
  hunters = true,
  leaders = true,          -- игрок убил/заковал лидера города из пар дирижёра -> кризис наследования, слух, реакции соседей
  banter = true,           -- свой из отряда игрока коротко отзывается о деле (Character:say), не чаще раза в banter_gap_s
  banter_p = 0.6,
  banter_gap_s = 240,
  banter_delay_s = 9,
  traits = true,           -- ХАРАКТЕРЫ: у части своих черта (из имени, стабильно без сейва); на событие первым отзывается тот, чья черта о нём
  trait_p = 0.75,
  -- РЕПЛИКИ ОТРЯДА О МИРЕ: место недавнего боя из хроники дирижёра, голод своих (ванильный MedicalSystem.hunger, шкала KMM_Tempo),
  -- пустые прилавки / осада города, где стоит отряд (KMM_Stock). Один раз на событие/город-день; не чаще amb_gap_s
  ambient = true,
  amb_gap_s = 600,
  amb_after_banter_s = 90,
  amb_site_r = 3000,
  amb_site_days = 3,
  amb_hungry = 0.3,        -- доля шкалы hunger_full: ниже (при hunger_dir = -1) — голоден
  amb_stock_low = 0.2,
  -- ШРАМЫ ОТРЯДА: свой лежал без сознания (ванильный isDown) — встав, роняет слово; через scar_days вспоминает место (ближайший город)
  night = true,            -- НОЧЬ В ПУТИ: вне города в ночные часы (час = игровые часы mod 24) — раз за ночь короткая реплика
  night_from = 22,
  night_to = 4,
  scars = true,
  scar_up_p = 0.5,
  scar_days = 1,
  scar_max = 12,
  -- ПЛЕННИКИ: закованный рядом с игроком, вырвавшийся не через взлом игрока (побег, отбили свои), — соперник «escaped»
  captives = true,
  max_captives = 10,
  captive_r = 1500,        -- заковали в этом радиусе от игрока = игрок
  escape_p = 0.8,
  -- ЗА СВОИМИ ПРИХОДЯТ: пленник всё ещё в цепях через rescue_after_h игровых часов — его фракция иногда шлёт отряд к игроку
  warlords = true,         -- пощажён warlord_met раз — поднимает спящего варлорда из доли своей банды (модель дирижёра)
  warlord_met = 3,
  -- СОПЕРНИКИ-НАЁМНИКИ: игрок стал заметен (есть соперник или прозвище) — именная компания наёмников идёт теми же дорогами:
  -- иногда забирает награду за соперника игрока раньше него, раз в несколько дней пересекается с ним (капитан отзывается о деле)
  company = true,
  co_factions = { "Mercenary Guild", "Adventurers Guild" },
  co_steal_p = 0.04,       -- в день на одного соперника игрока
  co_meet_days = 5,
  co_meet_p = 0.35,
  titles = true,           -- ПРОЗВИЩЕ ИГРОКА: мир зовёт его по делам (слух при смене, в текстах событий и у горожан)
  rescue = true,
  rescue_after_h = 6,
  rescue_p = 0.5,
  rescue_cd_days = 3,
  -- ГОРОД ПОМНИТ: игрок в городе рядом с местом своего дела — горожанин рядом заговаривает о нём (раз на дело)
  town_talk = true,
  talk_gap_s = 120,
  talk_r = 4000,           -- дело было не дальше от игрока
  talk_speaker_r = 700,
  talk_min_days = 0.5,     -- весть должна разойтись
  talk_max_days = 40,
  max_deeds = 20,
  -- ГОРОД ВСТРЕЧАЕТ: игрок вошёл в город — житель фракции-хозяина (снимок KMM_Gov) говорит по положению дел: прозвище игрока,
  -- смена хозяина (хроника дирижёра), беспорядки и убыль населения (town_mood), отношение хозяина к игроку (модель дирижёра)
  -- ТОРГОВЕЦ ГОВОРИТ О РЫНКЕ: открыто окно торговли (ForgottenGUI::showTradeWindow) — торговец роняет реплику по складу города
  -- (KMM_Stock: осада, дефицит еды/металла/оружия, избыток) и цене (price_mult_town). Раз в день на торговца; молчит, когда всё обычно
  shop_talk = true,
  shop_gap_s = 45,
  shop_low = 0.2,
  shop_glut = 1.3,
  shop_dear = 1.25,
  -- ХРОНИКА В ЖУРНАЛЕ: крупные события мира из хроники дирижёра (захват города, бунт, наследование, договоры, голод, набег на базу)
  -- -> вкладка сообщений окна управления (ManagementScreen.getSingleton():addMessage, ENGINE_FINDINGS). По одному раз в chron_gap_s, очередь ≤ chron_queue
  chronicle = true,
  chron_gap_s = 15,
  chron_queue = 12,
  chron_owner = "Chronicle",
  chron_near_r = 5000,     -- дальние вести несёт KMM_Rumors (с задержкой пути); в журнал сразу — только то, что рядом или про игрока
  greet = true,
  greet_delay_s = 25,
  greet_cd_days = 1.5,
  greet_owner_days = 10,
  mourn_days = 5,          -- ТРАУР: лидер города убит/закован недавно — житель говорит о нём при входе (раньше прочих тем)
  greet_unrest = 0.6,
  greet_pop = 0.6,
  greet_cold = -20,
  greet_warm = 40,
  legend_min = 6,          -- ЛЕГЕНДА: при прозвище и ≥ N делах (счётчики прозвищ) житель города раз на город пересказывает их как байку
  intel = true,            -- ОСВЕДОМИТЕЛИ: есть должник и живой соперник — горожанин передаёт весть, где соперника видели
  intel_gap_days = 2,
  hunter_max_bonus = 1,    -- +тир охотника после поражения от игрока
  -- ДЕЛА ЯДРА (Q3): шина KMM_Deeds (type="deed" из FactionRelations::affectRelations). Фракция помогла игроку — помощник рядом
  -- запоминает его (LT_FRIENDLY_AQUAINTANCE через плагин) и говорит: долг перед игроком закрыт или теперь игрок должен.
  -- Игрок ударил/выручил фракцию-хозяина города — запись в X.deeds: её скажут town_talk и greet (раз на дело)
  deeds = true,
  aid_r = 3000,            -- помощник ищется в снимке KMM_Gov не дальше от игрока
  owe_days = 18,           -- долг игрока перед фракцией забывается
  vanilla_lines = true,    -- ванильная реплика (Character:sendDialogEvent), где повод совпадает; не сработала — наша строка
  vanilla_fail_max = 3,    -- столько ошибок вызова — дальше только наши строки
  -- Y5 ОЦЕНКА ПРИ ВСТРЕЧЕ: подойдя к игроку, главарь соперника сравнивает ВИДИМУЮ силу отряда игрока (StateBroadcastData.apparentStrength
  -- своих, кого он видит и кто на ногах; дух сломлен — Blackboard.moraleIsBroken) со своей (actualStrength главаря x размер отряда):
  -- слабее — нападает (пакет охоты S3), сильнее — уходит (пакет «бродить», ванильная реплика отказа от погони), между — угрожает и
  -- пересматривает через appr_parley_s. Только чтение полей ядра; не прочиталось/не подошёл — как раньше (пакет охоты)
  appraise = true,
  appr_r = 2000,           -- главарь ближе к своему игрока — оценивает (масштаб единиц ?)
  appr_seen_r = 3500,      -- свои игрока дальше от главаря в оценку не входят
  appr_max_s = 600,        -- не подошёл/никого не увидел за это время — фолбэк
  appr_attack = 0.8,       -- видимая сила игрока / сила банды ниже — нападает
  appr_flee = 1.6,         -- выше — уходит
  appr_parley_s = 30,
  appr_broken = 0.5,       -- дух отряда игрока сломлен: видимая сила x
  appr_regroup_days = 2,   -- ушедший постоянный соперник снова берёт след (пакет охоты)
  appr_withdraw_days = 2,  -- окно отхода: в нём повторный отход того же соперника не даёт нового события, KMM_Nemesis.withdrew_recent = true
  -- ПРЕЗРЕНИЕ (contempt): отряд игрока слабее (ratio < appr_attack) и взять с него нечего (N.worth: деньги ядра, цена надетого и носимого,
  -- награда ядра, прозвище по делам, численность, навык) — соперник не нападает ради добычи: пакет «бродить», реплика, регрупп через
  -- appr_regroup_days, при следующей встрече оценка снова. Разбогател / прославился — та же оценка даёт штурм. Мститель (avenger) не презирает.
  appr_contempt = true,
  appr_contempt_days = 2,  -- окно: повторное презрение того же соперника без нового события
  worth_money = 1000,      -- деньги игрока (Ownerships:getMoney) не больше
  worth_gear = 2500,       -- суммарная цена вещей своих (InventoryItemBase:getValueAll) не больше
  worth_bounty = 0,        -- награда ядра (CrimeManager:getTotalBounty) не больше
  worth_squad = 2,         -- живых своих не больше
  worth_skill = 25,        -- средний общий навык (CharStats:getOverallSkillLevel_0_100) не выше; не читается — не учитывается
  worth_ttl_s = 10,        -- кэш оценки богатства, реальные секунды
  worth_item_guess = 500,  -- цена вещи, если ни getValueAll, ни getValueSingle не читаются (маркер «worth: item value fallback=guess»)
  chron_type_day = 2,      -- ХРОНИКА: событий одного «ближнего» типа в журнал за игровой день не больше
  generic_rx = "bandit|thug|guard|soldier|hungry|starving|dust|raider|ninja|samurai|recruit|mercenary|slaver|hunter|warrior|cannibal|" ..
               "fogman|skeleton|drifter|outlaw|scout|sentry|paladin|knight|trader|worker|peasant|farmer|vagrant|thief|pirate|nomad|" ..
               "leader|boss|captain|sergeant|grunt|thrall|member|militia|patrol",
}
N.EPI = {
  spared = { "Who Got Up", "the Unbroken", "Grudgebearer", "Sandscar" },
  fled   = { "Lastlaugh", "the Runner", "Long-Memory" },
  beat   = { "the Boot", "Knuckles", "the Lesson", "Dustmaker" },
  again  = { "Twice-Spared", "the Stubborn", "Who Keeps Coming" },
  escaped = { "Chainbreaker", "Who Slipped the Collar", "the Uncaged" },
}
N.SAY = {
  spared = { "You left me in the dirt near %s. I didn't stay there.", "Remember %s? I do. Every night.", "%s. You should have finished it." },
  fled   = { "I ran at %s. I'm done running.", "You chased me off at %s. Now I've brought friends." },
  beat   = { "Back for more? I left you in the sand at %s.", "You again. %s wasn't lesson enough?", "I remember you. Face down at %s." },
  avenger = { "%s was mine to bury. You put him there.", "You killed %s. I came to collect.", "They still talk about %s. Nobody will talk about you." },
  again  = { "Again? You keep leaving me alive. Mistake.", "%s, and now this. Third time ends it." },
}
N.SAY.escaped = { "You put me in chains near %s. Chains break.", "%s. I still feel the collar.", "Remember the cage at %s? I got out." }
N.TALK = {
  debt_made_healed = { "Heard you patched up %s around here. Decent of you.", "%s says you stopped the bleeding. Not many would.", "You are the one who helped %s. People noticed." },
  debt_made_freed = { "You cut %s loose. Some here liked that. Some did not.", "%s walks free because of you. Word gets around.", "Breaking chains, now? %s told everyone." },
  nemesis_born_spared = { "%s still talks about you. Watch your back.", "You left %s alive. He did not take it as a kindness.", "%s asks about you in every bar." },
  nemesis_born_beat = { "%s laughs about you in every bar. Says you went down easy.", "%s beat you once and tells everyone.", "If you want your pride back, %s has it." },
  nemesis_born_fled = { "%s ran from you. He is not running anymore.", "%s is telling everyone how he got away from you.", "They say %s is gathering men. Because of you." },
  nemesis_born_avenger = { "%s swore an oath over a grave. Your name was in it.", "A man called %s is looking for you. Not to talk.", "Someone you killed had a friend. %s." },
  nemesis_born_escaped = { "%s got out of your chains. Folk here saw it.", "%s laughs about your locks.", "You lost a prisoner, I hear. %s." },
  nemesis_hunter_beaten = { "You put down %s. The hunters drink elsewhere now.", "%s limped through here, cursing you.", "%s will be back. Hunters always come back." },
  leader_fell = { "%s is gone because of you. Nobody here forgets that.", "So you are the one. %s. Things are different now.", "Since %s fell, everyone is nervous. Thanks for that." },
  -- дела ядра (KMM_Deeds): %s — имя фракции
  deed_killed = { "You killed %s folk around here. People have not forgotten.", "Blood of %s near here. They say it was you.", "%s buried their own because of you." },
  deed_executed = { "You executed a prisoner of %s. Nobody here forgets that.", "They say you cut down a %s captive in cold blood." },
  deed_captured = { "You dragged %s people off in chains. Word got here first.", "Folk say you took prisoners from %s near here." },
  deed_defeated = { "You beat %s fighters bloody near here. They are still limping.", "%s got a beating from you. People noticed." },
  deed_defended = { "You fought for %s around here. Some folk are grateful.", "They say you beat off the enemies of %s. Good work." },
  deed_ingrate = { "%s helped you once, and you paid them back with blood.", "Folk remember: %s stood by you, and you turned on them." },
  deed_owed = { "Heard %s pulled you out of a bad fight. You owe them.", "%s stood by you, I hear. Do not forget it." },
}
N.DEED_G = { killed = "killed", executed = "executed", captured = "captured", defeated = "defeated",
             aided = "defended", killed_enemy = "defended", defeated_enemy = "defended" }   -- вид дела ядра -> ключ строк города
N.EV = { EV_I_SEE_NEUTRAL_SQUAD = 3, EV_LAUNCH_ATTACK = 16, EV_BOUNTY_SPOTTED = 44, EV_KIDNAPPING_MY_ALLY = 58, EV_GIVE_UP_CHASE = 60,
         EV_I_SEE_ENEMY_PLAYER = 66 }   -- EnumsReference EventTriggerEnum (✓код)
N.SAY.appr_parley = { "Count your blades, Nameless. I am counting mine.", "Not here. Not yet. But I see you.", "Walk on. While I let you." }
N.SAY.appr_attack = { "Enough talk. Take them!", "They are breaking. Now!", "Look at them. Finish it." }
N.SAY.appr_contempt = { "Nothing on you worth the sweat. Walk.", "Look at you. Come back when you're worth robbing.", "Not worth the blade. Go on, crawl." }
N.SAY.appr_withdraw = { "Too many of you. Another day.", "Not today. I can wait.", "You got lucky. I know where you sleep." }
N.SAY.rescue = { "Where is %s? We know you took him.", "We came for %s. Hand him over or bleed.", "%s is one of ours. Nobody keeps him." }
N.TITLES = {   -- счётчик, порог, прозвище (побеждает наибольшее отношение счёт/порог ≥ 1)
  { "spared", 3, "the Merciful" }, { "freed", 3, "the Liberator" }, { "healed", 3, "the Kind" },
  { "leaders", 2, "Kingslayer" }, { "hunters", 2, "Hunterbane" }, { "graves", 3, "Gravefiller" },
}
N.TITLE_REL = {   -- прозвище -> отношение фракций к игроку (раз при получении, через модель дирижёра -> движок)
  ["the Liberator"] = { ["Anti-Slavers"] = 15, ["Slave Traders"] = -15, ["Slave Hunters"] = -10 },
  ["the Kind"] = { ["Guild of Surgeons"] = 10, ["Drifters"] = 5 },
  ["Hunterbane"] = { ["Bounty Hunters"] = -10 },
  ["the Merciful"] = { ["Drifters"] = 5 },
}
N.CNT = { debt_made_healed = "healed", debt_made_freed = "freed", nemesis_hunter_beaten = "hunters", nemesis_dead_byp = "graves" }
N.CO_NAMES = { "Sable Company", "the Ash Lanterns", "the Long Knives", "the Dry Wind Crew", "the Rust Banner" }
N.SAY.co_kill = { "We got %s before you did. No hard feelings.", "%s? Already collected. Be faster next time.", "Shame about %s. For you, I mean. We got paid." }
N.SAY.co_title = { "So you are %s. We have heard.", "%s, is it? Same roads, same work.", "They call you %s. They call us when it matters." }
N.SAY.co_plain = { "Same roads, same ruins. Try to keep up.", "Another crew chasing coin. Stay out of our way.", "Nameless, right? We keep hearing that name." }
N.SAY.intel = { "A friend of %s asked me to tell you: %s was seen around %s.", "%s sends word: %s is in %s, asking about you.",
                "From %s, for you: %s. Last seen near %s." }
N.SAY.healed = { "You patched me up near %s. My turn.", "Remember %s? You stopped my bleeding. I don't forget.", "%s. You could have walked past. You didn't." }
N.SAY.freed = { "You cut my chains at %s. Now I cut for you.", "Free because of you, since %s. Let's go.", "%s. I told them who opened my shackles." }
N.SAY.hunt_first = { "%d on your head, Nameless. Nothing personal.", "The contract says %d. I always collect.", "%d cats. Come quietly or don't." }
N.SAY.hunt_again = { "Near %s you got lucky. The price went up.", "I got up after %s. Did you think I would quit?", "%s was a lesson. For you, this time." }
N.SAY.hunt_heir = { "You killed %s. The contract passed to me.", "%s trained me. Bad idea, killing him.", "They gave me the warrant of %s. And his grudge." }
N.HT = { "the Collector", "Warrant", "the Ledger", "Iron Writ", "the Patient", "Long Rope", "Black Seal", "the Tally" }
N.AMB = {
  site = { "Blood in the sand. %s was hit here not long ago.", "Fresh graves outside %s. Someone fought here.", "Smoke has barely cleared over %s.",
           "Look at %s. Whoever came through did not ask nicely." },
  hungry = { "When did we last eat?", "My stomach is eating itself.", "We need food. Soon.", "Cannot fight on an empty belly." },
  empty = { "Look at the stalls. Empty.", "Nothing to eat in %s. Bad times.", "Even the bread is gone in %s." },
  wreck = { "Look. A %s caravan. Nobody left alive.", "%s colours on the bodies. Picked clean already.", "Someone ambushed a %s caravan here. Keep your eyes open." },
  night = { "Cold tonight. Keep close.", "Something is moving out there.", "Stars are out. Keep the fire low.", "I hate the road at night.",
            "Hear that? ...Never mind." },
  up = { "Still breathing. Barely.", "I am fine. I am fine.", "Who hit me? Never mind. Later.", "Help me up. My legs are not listening." },
  scar = { "That fight near %s still haunts me.", "I keep dreaming about %s.", "Near %s I thought it was over for me.", "My ribs still remember %s." },
  siege = { "They are under siege. Prices will be murder.", "%s is surrounded. We picked a bad time.", "Walls of %s are holding. For now." },
}
N.GREET = {
  title = { "So you are %s. Keep it civil here.", "%s. We heard. Do not make trouble in our town.", "Look who walked in. %s, they say." },
  owner = { "%s run this place now. Keep your head down.", "New flags on the walls. %s. Same work for us.", "%s took the town. Taxes went up the next day." },
  unrest = { "People are angry. Something will burn soon.", "Watch yourself. The whole town is one spark away.", "Nobody pays the guards anymore. Not for long." },
  pop = { "Half the town is gone. Raids, hunger, slavers.", "Empty houses everywhere. You picked a sad place.", "We used to be more. Then the raids started." },
  cold = { "Keep walking. We know your kind.", "Do not linger. The guards are watching you.", "You are not welcome here. Remember that." },
  warm = { "Good to see you again, friend.", "Ah, you. Trouble is quieter when you are around.", "Welcome back. Drinks are cheaper for friends." },
}
N.GREET.deed = {   -- житель фракции-хозяина о деле игрока против/за его фракцию (KMM_Deeds)
  killed = { "You killed our people. We have not forgotten.", "Our dead are barely cold, and you walk in here.", "Murderer. The guards know your face." },
  executed = { "You executed one of ours. Leave while you can.", "We know what you did to our prisoner." },
  captured = { "Where are the ones you dragged off in chains? We remember.", "You took our people as prisoners. Bold of you to come here." },
  defeated = { "You beat our people bloody. Keep your hands where we can see them.", "Some of ours are still limping because of you." },
  defended = { "You fought for us out there. Welcome.", "Thank you for what you did out there. People saw." },
  ingrate = { "We helped you once. Never again.", "We stood by you, and you paid us in blood." },
}
N.SAY.aid_owe = { "On your feet, Nameless. You owe us one.", "Remember who pulled you out of that.", "We will not always be around. Try to stay alive." }
N.SAY.aid_even = { "For %s near %s. Now we are square.", "%s told us about %s. Debt paid.", "You helped %s at %s. We remember too." }
N.SHOP = {
  siege = { "Prices doubled since the siege. Nothing gets through the gates.", "Under siege, friend. Pay or starve.", "Siege prices. Do not argue." },
  food = { "Bread is scarce. The caravans stopped coming.", "No meat this week. Not for any money.", "Food? I have a little. It will cost you." },
  metal = { "No iron this week. The mines are quiet.", "Metal is short. Everything with steel in it costs more.", "Smiths took all the plates. Sorry." },
  weapons = { "Blades sold out. Everyone is arming.", "Weapons? Half the town bought one this week.", "Not much steel left on my racks. Bad sign." },
  dear = { "Everything costs more now. Blame the roads.", "Prices are up. Raiders on every road.", "Do not look at me like that. My suppliers charge me double." },
  glut = { "Shelves are full. Buy while it lasts.", "Too much stock, too few buyers. Make me an offer.", "Caravans came in. Good day to buy." },
}
N.LEGEND = { spared = "spared %d who begged on the road", freed = "cut the chains of %d slaves", healed = "patched up %d strangers in the dirt",
             leaders = "brought down %d town lords", hunters = "sent %d bounty hunters home crawling", graves = "dug %d graves for those who came hunting" }
N.LEGEND_FMT = { "They tell it in every bar: %s %s, and %s.", "Kids play at being %s now. The one who %s, and %s.", "Heard the story? %s %s, and %s. Is it true?" }
function N.legend_line(S, tsid)   -- байка о деяниях игрока или nil
  local cfg = N.cfg()
  local X = N.state(S)
  if not (X.title and X.cnt) or (X.legend and X.legend[tsid]) then return nil end
  local L, tot = {}, 0
  for k, v in pairs(X.cnt) do if N.LEGEND[k] and v > 0 then L[#L + 1] = { k, v }; tot = tot + v end end
  if tot < cfg.legend_min or #L < 2 then return nil end
  table.sort(L, function(a, b) return a[2] > b[2] or (a[2] == b[2] and a[1] < b[1]) end)
  local fmt = N.pick(N.LEGEND_FMT)
  local a, b = string.format(N.LEGEND[L[1][1]], L[1][2]), string.format(N.LEGEND[L[2][1]], L[2][2])
  local ttl = X.title:gsub("^%l", string.upper)
  return string.format(fmt, ttl, a, b)
end
N.CHRON_EV = { town_captured = true, revolt = true, town_rejoined = true, warlord_rose = true, succession_crisis = true, succession_resolved = true,
               faction_split = true, faction_fell = true, faction_rise = true, treaty_signed = true, treaty_broken = true, betrayal = true,
               famine = true, chaos_incursion = true, settlement_founded = true, mine_exhausted = true, leader_killed = true, leader_captured = true,
               slave_raid = true, base_raid = true, base_campaign = true, base_raid_repelled = true, base_raid_unattended = true, base_raid_sacked = true, ally_joins = true,
               nemesis_title = true, nemesis_company = true, nemesis_warlord = true }
-- значимые дела рядом с игроком (только в chron_near_r или про игрока), не больше chron_type_day одного типа за игровой день, без повтора текста
N.CHRON_NEAR = { raid = true, attack_repelled = true, caravan_lost = true, waylay = true, outlaw_racket = true, outlaw_manhunt = true, outlaw_dead = true,
                 fate_death = true, fate_wounded = true, fate_defect = true, slaves_freed = true, predator_nest = true, predator_patrol = true,
                 ruin_expedition = true, bounty_hunters = true, ally_help = true, ally_failed = true, outlaw_pc_wanted = true,
                 nemesis_born = true, nemesis_dead = true, nemesis_withdrew = true, nemesis_contempt = true, nemesis_beat_again = true,
                 nemesis_hunter_beaten = true, nemesis_hunter_dead = true }
N.CHRON_PLAYER = { nemesis_title = true, nemesis_company = true, base_raid = true, base_campaign = true, base_raid_repelled = true, base_raid_unattended = true, base_raid_sacked = true, ally_joins = true }
function N.chron_known(C, ev)   -- игрок мог узнать сразу: событие про него или рядом
  if N.CHRON_PLAYER[ev.type] or ev.by_player then return true end
  local okp, pf = pcall(function() return C.cfg().player_faction end)
  if okp and pf and (ev.a == pf or ev.b == pf) then return true end
  local px, pz = N.player_pos()
  if not px then return false end
  local x, z = ev.x, ev.z
  if not x and ev.town_sid then
    local okI, I = pcall(function() return C.cfg().town_info[ev.town_sid] end)
    if okI and I then x, z = I.x, I.z end
  end
  return x ~= nil and (x - px) ^ 2 + (z - pz) ^ 2 < N.cfg().chron_near_r ^ 2
end
function N.chron_room(ev, cfg)   -- «ближний» тип: лимит за игровой день и без повтора текста (редкие крупные — как раньше)
  if N.CHRON_EV[ev.type] then return true end
  local d = math.floor(ev.day or 0)
  N.chron_n = N.chron_n or {}
  N.chron_txt = N.chron_txt or {}
  local r = N.chron_n[ev.type]
  if not r or r.d ~= d then r = { d = d, n = 0 }; N.chron_n[ev.type] = r end
  if r.n >= cfg.chron_type_day or N.chron_txt[ev.text] then return false end
  r.n = r.n + 1
  N.chron_txt[ev.text] = true
  N.chron_tn = (N.chron_tn or 0) + 1
  if N.chron_tn > 200 then N.chron_txt, N.chron_tn = {}, 0 end
  return true
end
function N.chronicle(C, S)
  local cfg = N.cfg()
  if not cfg.chronicle or N.chron_off then return end
  local X = N.state(S)
  local E = S.events or {}
  local last = E[#E] and E[#E].id or 0
  if not X.chron_id then X.chron_id = last; return end   -- первая загрузка: историю не вываливаем
  N.chron_q = N.chron_q or {}
  if #N.chron_q == 0 or not N.chron_qi then N.chron_qi = {} end   -- id строк очереди (для KMM_Nemesis.chronicled)
  if last > X.chron_id then
    for i = math.max(1, #E - 200), #E do
      local ev = E[i]
      if ev.id and ev.id > X.chron_id and (N.CHRON_EV[ev.type] or N.CHRON_NEAR[ev.type]) and ev.text and ev.text ~= "" and N.chron_known(C, ev)
         and N.chron_room(ev, cfg) then
        N.chron_q[#N.chron_q + 1] = string.format("Day %d. %s", math.floor(ev.day or 0), ev.text)
        N.chron_qi = N.chron_qi or {}
        N.chron_qi[#N.chron_q] = ev.id
        if #N.chron_q > cfg.chron_queue then table.remove(N.chron_q, 1); table.remove(N.chron_qi, 1) end
      end
    end
    X.chron_id = last
  end
  local now = os.clock()
  if #N.chron_q == 0 or now - (N.chron_t or -1e9) < cfg.chron_gap_s then return end
  local MS = rawget(_G, "ManagementScreen")
  local ok, ms = pcall(function() return MS and MS.getSingleton() end)
  if not (ok and ms) then return end   -- окно ещё не создано (ранняя загрузка) — строки ждут в очереди
  local line = table.remove(N.chron_q, 1)
  local lid = N.chron_qi and table.remove(N.chron_qi, 1) or nil
  if lid then   -- то же событие Rumors уже записал в журнал (KMM_Rumors.journaled): второй строки не пишем; нет функции — как раньше
    local R = rawget(_G, "KMM_Rumors")
    local okj, jd = false, false
    if type(R) == "table" and type(R.journaled) == "function" then okj, jd = pcall(R.journaled, lid) end
    if okj and jd == true then
      N.chron_sent = N.chron_sent or {}; N.chron_sent[lid] = true
      N.log("chronicle: skip event " .. tostring(lid) .. " - already in the journal via Rumors")
      return
    end
  end
  local col = rawget(_G, "MessageLogColor")
  local okc, c2 = pcall(function() return col and col.ML_SYSTEM end)
  local oka, ea = pcall(function() ms:addMessage(cfg.chron_owner, line, (okc and c2) or 2) end)
  N.chron_t = now
  -- B8: маркер вызова движка (успех — один раз за сессию, ошибка — всегда) для session_report
  if not oka then N.chron_off = true; N.log("chronicle disabled until restart: addMessage FAILED: " .. tostring(ea)); return end
  if not N.chron_ok_logged then N.chron_ok_logged = true; N.log("chronicle: addMessage ok (ManagementScreen message log)") end
  if lid then   -- KMM_Nemesis.chronicled(id): это событие уже во вкладке сообщений (Rumors не пишет его второй раз)
    N.chron_sent = N.chron_sent or {}; N.chron_sn = (N.chron_sn or 0) + 1
    if N.chron_sn > 400 then N.chron_sent, N.chron_sn = {}, 1 end
    N.chron_sent[lid] = true
  end
  N.log("chronicle: " .. line)
end
N.MOURN = { leader_killed = { "We buried %s not long ago. Show some respect.", "%s is dead. Nobody knows who is in charge now.", "They killed %s. The whole town is holding its breath." },
           leader_captured = { "They dragged %s off in chains. Who rules us now?", "%s is in someone's cage. The guards are nervous.", "No word from %s since they took him. Bad times." } }
N.GREET_EV = { town_captured = true, revolt = true, town_rejoined = true }
N.AMB_EV = { raid = true, town_captured = true, attack_repelled = true, revolt = true, leader_killed = true }
N.TRAITS = {
  coward = { nemesis_hunter = { "We could just... run? Nobody would know.", "Bounty hunters. I hate this. I hate all of this." },
             nemesis_return = { "Not them again. Please not them.", "Can we not fight today? Just once?" },
             nemesis_rescue = { "More of them. Always more of them." } },
  greedy = { nemesis_dead = { "Did he have anything worth taking?", "Check his pockets before the vultures do." },
             leader_fell = { "Who gets his money now? Asking for a friend." },
             nemesis_hunter_dead = { "Bounty hunters carry coin. Search him." } },
  veteran = { nemesis_born = { "Leave enemies alive and they come back. Every time.", "Seen this before. He will return with friends." },
              nemesis_hunter_beaten = { "Sloppy. He telegraphed every swing.", "Hired steel. No heart in it." },
              nemesis_return = { "Form up. Shields to the front. This one knows us." } },
  softhearted = { debt_made = { "I am glad we stopped. Really.", "That was the right thing." },
                  nemesis_dead = { "He had a mother too, you know.", "I wish it had ended another way." },
                  debt_repaid = { "See? People remember kindness." } },
  freeborn = { debt_made_freed = { "Nobody should wear chains. Nobody.", "Cut them all loose, every last one." },
               nemesis_rescue = { "Slavers. I will not let them take anyone." },
               leader_fell = { "One less master. Good." } },
}
N.TRAIT_KEYS = { "coward", "greedy", "veteran", "softhearted", "freeborn" }
function N.trait_of(nm)   -- черта по имени (стабильная): nil у части отряда
  if type(nm) ~= "string" or nm == "" then return nil end
  local h = 7
  for i = 1, #nm do h = (h * 31 + nm:byte(i)) % 1000003 end
  return N.TRAIT_KEYS[h % (#N.TRAIT_KEYS + 3) + 1]   -- +3: примерно 3 из 8 без черты
end
N.BANTER = {
  nemesis_born = { "We should have finished that one.", "He will be back. They always come back.", "Mercy is a long road." },
  debt_repaid = { "Told you. Kindness pays, sometimes.", "Look who remembered us.", "Good. We need every blade." },
  debt_made = { "Hope that one remembers.", "Not every fight is with a sword.", "Done. Let us move." },
  nemesis_hunter = { "Bounty hunters. Of course.", "Someone wants our heads badly.", "Him again?" },
  nemesis_hunter_beaten = { "Leave him. Word will travel.", "He will want a rematch.", "Not so tough now." },
  nemesis_hunter_dead = { "There will be another one.", "Someone else will pick up that paper.", "That was not the last of them." },
  nemesis_dead = { "Finally. Buried.", "That grudge is over.", "One less shadow on the road." },
  nemesis_rescue = { "They came for the prisoner.", "Here come his friends.", "Should have sold him faster." },
  nemesis_return = { "Riders on the ridge. I know that banner.", "Dust behind us. Someone has been following.", "It is them again. Weapons out." },
  nemesis_withdrew = { "Look at him go. He counted us.", "He will be back with more men.", "Smart. Not brave, but smart." },
  nemesis_title = { "Did you hear what they call us now?", "A name. Great. Now everyone knows who to hunt.", "They are telling stories about us in the bars." },
  leader_fell = { "This changes things around here.", "They will fight over the seat now.", "We just made a lot of enemies. And some friends." },
}
N.SYL_A = { "Ka", "Ro", "Mu", "Ve", "Sa", "Dro", "Ti", "Ga", "Yo", "Ne", "Bra", "Ul" }
N.SYL_B = { "rek", "dan", "sh", "ro", "mok", "zel", "ga", "th", "vin", "lo" }

function N.log(msg)
  if N.nlog >= N.DEF.log_max then return end
  N.nlog = N.nlog + 1
  local ok, f = pcall(io.open, "C:/KenshiModMap/logs/nemesis.log", "a")
  if ok and f then f:write(os.date("%Y-%m-%d %H:%M:%S"), " ", tostring(msg), "\n"); f:close() end
  pcall(function() if KenshiLua and KenshiLua.log then KenshiLua.log(TAG .. tostring(msg)) end end)
end
function N.fail(where, err) N.off = true; N.log("disabled until restart in " .. where .. ": " .. tostring(err)) end
-- Конфиг: params.nemesis поверх N.DEF без копирования (~150 ключей на вызов было бы дорого каждый кадр). Прокси на ту же таблицу params:
-- чтение ключа — params, иначе N.DEF; запись в прокси уходит в params. Правка params.nemesis.X видна сразу; новая таблица params — новый прокси.
N.CFG_MT = {}
function N.cfg()
  local ok, p = pcall(function() return KMM_Conductor.cfg().params.nemesis end)
  if not (ok and type(p) == "table") then return N.DEF end
  if N.cfg_p == p and N.cfg_px then return N.cfg_px end
  local D = N.DEF
  N.cfg_p = p
  N.cfg_px = setmetatable({}, { __index = function(_, k) local v = p[k]; if v == nil then v = D[k] end; return v end,
                                 __newindex = function(_, k, v) p[k] = v end })
  return N.cfg_px
end
function N.pick(t) return t[math.random(1, #t)] end
function N.state(S)
  S.ext = S.ext or {}
  local X = S.ext.nemesis
  if type(X) ~= "table" then X = { v = 1, last_new = -1000, born = 0, dead = 0, met = 0 }; S.ext.nemesis = X end
  return X
end
function N.day(C)
  local ok, d = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalDays() end)
  if ok and type(d) == "number" then return d end
  local okc, s = pcall(C.state)
  return okc and s and s.last_day or 0
end
function N.player_pos()
  local ok, x, z = pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local p = c:getPosition()
      if p then return p.x, p.z end
    end
  end)
  if ok then return x, z end
end
function N.player_name()
  local ok, nm = pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do local n = c:getName(); if n and n ~= "" then return n end end
  end)
  return ok and nm or nil
end
function N.where(D, x, z)   -- ближайший город (имя) и его регион
  if not (D and x) then return nil, nil end
  local best, bd, brg = nil, math.huge, nil
  for rg, r in pairs(D.regions or {}) do
    for _, t in ipairs(r.towns or {}) do
      local d = (t.x - x) ^ 2 + (t.z - z) ^ 2
      if d < bd then best, bd, brg = t, d, rg end
    end
  end
  return best, brg
end
function N.outlaws()
  local O_ = rawget(_G, "KMM_Outlaws")
  local C = rawget(_G, "KMM_Conductor")
  if not (O_ and O_._M and C and C.state) then return nil end
  local S = C.state()
  if type(S) ~= "table" or not S.F then return nil end
  local M = O_._M
  local D = M.data(C)
  if not D then return nil end
  return M, M.O(S), D, C, S
end
function N.rivals(O)
  local out = {}
  for _, o in pairs(O.L) do if o.pg and o.st == "a" then out[#out + 1] = o end end
  table.sort(out, function(a, b) return a.i < b.i end)
  return out
end
function N.find(O, name)
  for _, o in pairs(O.L) do
    if o.pg and (o.n == name or o.pg.base == name) then return o end
    if o.pg and o.pg.aka then for _, a in ipairs(o.pg.aka) do if a == name then return o end end end
  end
end
function N.base_name(nm)   -- у безымянных («Hungry Bandit») — новое имя; у именных — своё
  local cfg = N.cfg()
  local low, gen = (nm or ""):lower(), false
  for w in cfg.generic_rx:gmatch("[^|]+") do if low:find(w, 1, true) then gen = true; break end end   -- в шаблонах Lua нет «|»
  if not nm or nm == "" or gen or select(2, nm:gsub("%S+", "")) > 2 then
    return N.pick(N.SYL_A) .. N.pick(N.SYL_B), true
  end
  return nm, false
end
function N.count(S, k)
  if not (S and N.cfg().titles) then return end
  local X = N.state(S)
  X.cnt = X.cnt or {}
  X.cnt[k] = (X.cnt[k] or 0) + 1
  local best, bs = nil, 0.999
  for _, t in ipairs(N.TITLES) do
    local sc = (X.cnt[t[1]] or 0) / t[2]
    if sc > bs then best, bs = t[3], sc end
  end
  if best and best ~= X.title then
    local old = X.title
    X.title = best
    local C = rawget(_G, "KMM_Conductor")
    X.title_rel = X.title_rel or {}
    if C and N.TITLE_REL[best] and not X.title_rel[best] then   -- слава меняет отношение тех, кому это важно (один раз на прозвище)
      X.title_rel[best] = true
      local pf = C.cfg().player_faction
      for fid in pairs(S.F or {}) do
        local okn, nm = pcall(C.name, fid)
        local dv = okn and N.TITLE_REL[best][nm]
        if dv and fid ~= pf then pcall(C.add_rel, fid, pf, dv) end
      end
    end
    if C then N.emit(C, nil, "nemesis_title", old and string.format("They used to call the Nameless %s. Now folk say %s.", old, best)
                                              or string.format("Folk have started calling the Nameless %s.", best), { title = best }) end
  end
end
function N.title(C)
  local okS, S = pcall(C.state)
  return okS and S and N.cfg().titles and N.state(S).title or nil
end
-- БОГАТСТВО И СЛАВА ИГРОКА — только ванильные числа (общее правило для любого момента игры, без привязки к старту):
-- деньги (PlayerInterface/Platoon Ownerships:getMoney), цена вещей своих (InventoryItemBase:getValueAll), награда ядра
-- (Character.crimes:getTotalBounty), прозвище по делам (N.title), численность и средний навык (CharStats:getOverallSkillLevel_0_100).
-- poor = взять нечего и бояться некого. Деньги не прочитались — poor = false (поведение как раньше). Кэш worth_ttl_s.
function N.worth(C)
  local cfg = N.cfg()
  local now = os.clock()
  if N.wc and now >= N.wc.t and now - N.wc.t < cfg.worth_ttl_s then return N.wc end
  local W = { t = now, gear = 0, bounty = 0, n = 0 }
  local sk, nsk = 0, 0
  pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      if W.n >= 30 then break end
      local okd, dead = pcall(function() return pc:isDead() end)
      if not (okd and dead == true) then
        W.n = W.n + 1
        if W.money == nil then   -- деньги общие на фракцию игрока: Character:getMoney (BindingsReference), запас — Ownerships платуна
          local okc, cm = pcall(function() return pc:getMoney() end)
          if okc and type(cm) == "number" then W.money = cm
          else
            local okp, pm = pcall(function() return pc:getPlatoon().me:getOwnerships():getMoney() end)
            if okp and type(pm) == "number" then W.money = pm end
          end
        end
        local okb, b = pcall(function() return pc.crimes:getTotalBounty() end)
        if okb and type(b) == "number" and b > 0 then W.bounty = W.bounty + b end
        local oks, v = pcall(function() return pc:getStats():getOverallSkillLevel_0_100() end)
        if oks and type(v) == "number" then sk, nsk = sk + v, nsk + 1 end
        pcall(function()   -- цена: getValueAll (InventoryItemBase), запас getValueSingle x quantity, не читается — worth_item_guess за вещь
          for _, it in ipairs(pc:getInventory():getAllItems()) do
            local okv, iv = pcall(function() return it:getValueAll(false) end)
            if not (okv and type(iv) == "number") then
              okv, iv = pcall(function() return it:getValueSingle(false) * (tonumber(it.quantity) or 1) end)
              if okv and type(iv) == "number" then W.fb = "single" else iv = cfg.worth_item_guess; W.fb = "guess" end
            end
            if type(iv) == "number" and iv > 0 then W.gear = W.gear + iv end
          end
        end)
      end
    end
  end)
  W.skill = nsk > 0 and sk / nsk or nil
  W.title = C and N.title(C) or nil
  W.poor = W.money ~= nil and W.n >= 1 and W.money <= cfg.worth_money and W.gear <= cfg.worth_gear and W.bounty <= cfg.worth_bounty
           and W.n <= cfg.worth_squad and not W.title and (W.skill == nil or W.skill <= cfg.worth_skill)
  W.txt = string.format("money=%s gear=%d%s bounty=%d n=%d skill=%s title=%s poor=%s", tostring(W.money), math.floor(W.gear),
                        W.fb and ("(" .. W.fb .. ")") or "", math.floor(W.bounty), W.n,
                        W.skill and string.format("%.0f", W.skill) or "?", tostring(W.title or "-"), tostring(W.poor))
  if W.fb and N.worth_fb ~= W.fb then   -- маркер: цена вещей посчитана запасным путём (раз на способ за сессию)
    N.worth_fb = W.fb
    N.log("worth: item value fallback=" .. W.fb .. (W.fb == "guess" and (" (getValueAll/getValueSingle unavailable, " .. cfg.worth_item_guess .. " per item)") or " (getValueAll unavailable)"))
  end
  N.wc = W
  return W
end
function N.poor(C)   -- безопасно: ошибка чтения -> false (как раньше)
  local ok, W = pcall(N.worth, C)
  return ok and type(W) == "table" and W.poor == true
end
function N.emit(C, o, typ, text, extra)
  local ttl = typ ~= "nemesis_title" and N.title(C)
  if ttl then text = text:gsub("([Tt]he Nameless)", "%1 they call " .. ttl, 1) end
  local ev = { type = typ, a = o and o.g, b = o and o.lf, leader_name = o and o.n, region = o and o.r, town_sid = o and o.s, text = text,
               player_name = N.player_name() }
  if extra then for k, v in pairs(extra) do ev[k] = v end end
  pcall(C.emit, ev)
  N.log(typ .. ": " .. text)
  N.banter(typ, extra and extra.deed)
  local ck = N.CNT[typ .. ((extra and extra.deed) and ("_" .. extra.deed) or (extra and extra.by_player and "_byp") or "")]
  if ck then pcall(function() N.count(C.state(), ck) end) end
  if extra and extra.x then N.deed_add(C, typ .. (extra.deed and ("_" .. extra.deed) or ""), ev.leader_name, extra.x, extra.z) end
end
function N.deed_add(C, k, who, x, z, ex)   -- дело игрока у места: город рядом его вспомнит; ex: fid, tsid, gk (строка greet)
  if not (N.TALK[k] and who and x and z) then return end
  local okS, S = pcall(C.state)
  if not (okS and S) then return end
  local X = N.state(S)
  X.deeds = X.deeds or {}
  local d = { k = k, who = who, x = x, z = z, day = N.day(C) }
  if ex then for kk, v in pairs(ex) do d[kk] = v end end
  X.deeds[#X.deeds + 1] = d
  while #X.deeds > N.cfg().max_deeds do table.remove(X.deeds, 1) end
  return d
end
function N.deed_greet(S, tsid, owner, day)   -- свежее дело игрока против/за хозяина этого города: (строка, запись) или nil
  local X = N.state(S)
  local D = X.deeds or {}
  for i = #D, 1, -1 do
    local d = D[i]
    if not d.said and d.gk and N.GREET.deed[d.gk] and d.tsid == tsid and owner and d.fid == owner and day - d.day <= N.cfg().greet_owner_days then
      return N.pick(N.GREET.deed[d.gk]), d
    end
  end
end
function N.intel_line(S, X, day)   -- должник через горожанина: где видели соперника игрока
  local cfg = N.cfg()
  if not cfg.intel or day - (X.intel_day or -1000) < cfg.intel_gap_days then return nil end
  local debtor
  for _, d in pairs(X.debts or {}) do if not debtor or (not d.paid and debtor.paid) then debtor = d end end
  if not debtor then return nil end
  local _, O = N.outlaws()
  local list = {}
  for _, r in ipairs(O and N.rivals(O) or {}) do if r.r then list[#list + 1] = r end end
  if #list == 0 then return nil end
  local r = list[math.random(#list)]
  return string.format(N.pick(N.SAY.intel), debtor.n, r.n, r.r)
end
function N.town_speaker(px, pz, fid)   -- живой житель города рядом (снимок KMM_Gov); при fid — сперва из этой фракции
  local cfg = N.cfg()
  local G = rawget(_G, "KMM_Gov")
  local okS, snap = pcall(function() return G and G.snapshot and G.snapshot(5) end)
  if not (okS and snap and snap.list) then return nil end
  local best, bd, own, od
  for _, r in ipairs(snap.list) do
    if not r.dead then
      local d2 = (r.x - px) ^ 2 + (r.z - pz) ^ 2
      if d2 < cfg.talk_speaker_r ^ 2 and ((not bd or d2 < bd) or (fid and (not od or d2 < od))) then   -- ближе лучшего или ближе лучшего «своего»
        local okt, t = pcall(function() return r.town end)
        local okd, dn = pcall(function() return r.ch:isDead() or r.ch:isDown() or r.ch:isPlayerCharacter() end)
        if okt and t and okd and not dn then
          if not bd or d2 < bd then best, bd = r.ch, d2 end
          if fid and (not od or d2 < od) then
            local okf, f = pcall(function() local fa = r.ch:getFaction(); local gd = fa and (fa:getData() or fa.data); return gd and gd.stringID end)
            if okf and f == fid then own, od = r.ch, d2 end
          end
        end
      end
    end
  end
  return own or best
end
function N.greet_line(C, S, tsid, day)   -- что скажет город при входе: строка или nil
  local cfg = N.cfg()
  local mood = C.town_mood and C.town_mood(tsid) or {}
  local owner = mood.owner
  local pf = C.cfg().player_faction
  if owner and owner == pf then return nil, nil end
  local ttl = N.title(C)
  local r = (owner and pf) and C.rel(owner, pf) or 0
  local E0 = S.events or {}
  for i = #E0, math.max(1, #E0 - 300), -1 do   -- траур по лидеру города
    local ev = E0[i]
    if N.MOURN[ev.type] and ev.town_sid == tsid and ev.leader_name and (ev.day or 0) >= day - cfg.mourn_days then
      return string.format(N.pick(N.MOURN[ev.type]), ev.leader_name), owner
    end
  end
  local dl, dref = N.deed_greet(S, tsid, owner, day)   -- город помнит дело игрока против/за своих (KMM_Deeds)
  if dl then return dl, owner, "deed", dref end
  if ttl and r >= cfg.greet_cold then
    local leg = N.legend_line(S, tsid)
    if leg then return leg, owner, "legend" end
    return string.format(N.pick(N.GREET.title), ttl), owner
  end
  local E = S.events or {}
  for i = #E, math.max(1, #E - 300), -1 do
    local ev = E[i]
    if N.GREET_EV[ev.type] and ev.town_sid == tsid and owner and (ev.day or 0) >= day - cfg.greet_owner_days then
      local okn, on = pcall(C.name, owner)
      if okn and on and on ~= "" then return string.format(N.pick(N.GREET.owner), on), owner end
    end
  end
  if (mood.unrest or 0) >= cfg.greet_unrest then return N.pick(N.GREET.unrest), owner end
  if mood.pop and mood.pop0 and mood.pop0 > 0 and mood.pop < cfg.greet_pop * mood.pop0 then return N.pick(N.GREET.pop), owner end
  if owner and r <= cfg.greet_cold then return N.pick(N.GREET.cold), owner end
  if owner and r >= cfg.greet_warm then return N.pick(N.GREET.warm), owner end
  return nil, owner
end
function N.shop_line(C, tsid, fid)   -- реплика торговца по рынку города или nil
  local cfg = N.cfg()
  local K = rawget(_G, "KMM_Stock")
  if K and K.stock then
    local okst, st = pcall(K.stock, tsid)
    if okst and st and st.siege then return N.pick(N.SHOP.siege) end
    for _, cat in ipairs({ "food", "metal", "weapons" }) do
      local okl, lv = pcall(K.level, tsid, cat)
      if okl and type(lv) == "number" and lv >= 0 and lv < cfg.shop_low then return N.pick(N.SHOP[cat]) end
    end
  end
  local okm, m = pcall(function() return C.price_mult_town(fid, tsid) end)
  if okm and type(m) == "number" and m >= cfg.shop_dear then return N.pick(N.SHOP.dear) end
  if K and K.level then
    local okg, g = pcall(K.level, tsid, "food")
    if okg and type(g) == "number" and g > cfg.shop_glut and math.random() < 0.5 then return N.pick(N.SHOP.glut) end
  end
  return nil
end
function N.on_trade(a, b)
  local cfg = N.cfg()
  if not cfg.shop_talk then return end
  local now = os.clock()
  if now - (N.shop_t or -1e9) < cfg.shop_gap_s then return end
  local tr
  for _, h in ipairs({ a, b }) do
    local okc, ch = pcall(function() return h:getCharacter() end)
    if okc and ch and not N.is_player(ch) then tr = ch end
  end
  if not tr then return end
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state()
  if not S then return end
  local id = N.ident(tr)
  local okt, tsid = pcall(function() local t = tr:getCurrentTownLocation(); local gd = t and (t:getGameData() or t.data); return gd and gd.stringID end)
  if not (id and okt and tsid) then return end
  local X = N.state(S)
  X.shop = X.shop or {}
  local key, day = id.fid .. "|" .. id.n, N.day(C)
  if day - (X.shop[key] or -1000) < 1 then return end
  N.shop_t = now
  local line = N.shop_line(C, tsid, id.fid)
  X.shop[key] = day
  if line then N.said[#N.said + 1] = { leader = tr, line = line, t = now + 0.5, shop = true } end
end
function N.greet(C, S)
  local cfg = N.cfg()
  if not cfg.greet or N.greet_off then return end
  local pc, tsid
  pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local t = c:getCurrentTownLocation()
      if t then local gd = t:getGameData() or t.data; pc, tsid = c, gd and gd.stringID; break end
    end
  end)
  local now = os.clock()
  if not (pc and tsid) then N.greet_town, N.greet_visit = nil, nil; return end
  if N.greet_town ~= tsid then N.greet_town, N.greet_visit = tsid, nil; N.greet_at = now + cfg.greet_delay_s; return end
  if not N.greet_at or now < N.greet_at then return end
  if now - (N.talk_t or -1e9) < 30 then return end
  local X = N.state(S)
  X.greet = X.greet or {}
  local day = N.day(C)
  if day - (X.greet[tsid] or -1000) < cfg.greet_cd_days then N.greet_at = nil; return end
  local line, owner, tag, dref = N.greet_line(C, S, tsid, day)
  if not line then N.greet_at = nil; X.greet[tsid] = day; return end
  local okp, p = pcall(function() return pc:getPosition() end)
  if not (okp and p) then return end
  local who = N.town_speaker(p.x, p.z, owner)
  if not who then N.greet_at = now + 20; return end   -- никого рядом — повтор через 20 с
  N.greet_at = nil; X.greet[tsid] = day; N.talk_t = now; N.greet_visit = tsid   -- за этот визит город уже сказал (KMM_Nemesis.greet_said)
  if tag == "legend" then X.legend = X.legend or {}; X.legend[tsid] = true end
  if tag == "deed" and dref then dref.said = day end   -- то же дело town_talk уже не повторит
  N.said[#N.said + 1] = { leader = who, line = line, t = now + 1, talk = true, greet = true }
end
function N.town_talk(C, S)
  local cfg = N.cfg()
  if not cfg.town_talk or N.talk_off then return end
  local now = os.clock()
  if now - (N.talk_t or -1e9) < cfg.talk_gap_s then return end
  local X = N.state(S)
  local pc, px, pz
  pcall(function()
    for _, c in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      if c:getCurrentTownLocation() then local p = c:getPosition(); pc, px, pz = c, p.x, p.z; break end
    end
  end)
  if not pc then return end
  local day = N.day(C)
  local dd
  for _, d in ipairs(X.deeds or {}) do
    local age = day - d.day
    if not d.said and age >= cfg.talk_min_days and age <= cfg.talk_max_days and (d.x - px) ^ 2 + (d.z - pz) ^ 2 < cfg.talk_r ^ 2 then dd = d; break end
  end
  local intel = not dd and N.intel_line(S, X, day)
  if not (dd or intel) then return end
  N.talk_t = now - cfg.talk_gap_s + 20   -- говорящего нет — повтор через 20 с
  local best = N.town_speaker(px, pz, dd and dd.fid)   -- дело против фракции — сперва её житель
  if not best then return end
  N.talk_t = now
  if intel then
    X.intel_day = day
    N.said[#N.said + 1] = { leader = best, line = intel, t = now + 2, talk = true }
    return
  end
  dd.said = day
  local line = string.format(N.pick(N.TALK[dd.k]), dd.who)
  local ttl = N.title(C)
  if ttl and math.random() < 0.5 then line = ttl:gsub("^%l", string.upper) .. ", is it? " .. line end
  N.said[#N.said + 1] = { leader = best, line = line, t = now + 2, talk = true }
end
function N.squad_alive()   -- живые свои: список персонажей
  local L = {}
  pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local okd, dn = pcall(function() return pc:isDead() or pc:isDown() end)
      if okd and not dn then L[#L + 1] = pc end
    end
  end)
  return L
end
function N.ambient_line(C, S, L)   -- что сказать сейчас: (key, строка) или nil
  local cfg = N.cfg()
  local X = N.state(S)
  X.amb = X.amb or {}
  local A = X.amb
  local okp, p = pcall(function() return L[1]:getPosition() end)
  if not (okp and p) then return nil end
  local px, pz = p.x, p.z
  local day = N.day(C)
  local CF = C and C.cfg and C.cfg() or {}
  local TI = CF.town_info or {}
  local E = S.events or {}
  for i = #E, math.max(1, #E - 300), -1 do   -- место недавнего боя (не break по дню: дни событий в журнале не строго по порядку)
    local ev = E[i]
    if ev.type == "caravan_lost" and ev.by ~= "player" and ev.x and not A["ev" .. tostring(ev.id)] and (ev.day or 0) >= day - 1
       and (ev.x - px) ^ 2 + (ev.z - pz) ^ 2 < cfg.amb_site_r ^ 2 and ev.attacker and ev.attacker ~= "" then   -- остов каравана рядом (Traces)
      A["ev" .. tostring(ev.id)] = true
      return "wreck", string.format(N.pick(N.AMB.wreck), ev.attacker)
    end
    local I = ev.town_sid and TI[ev.town_sid]
    if N.AMB_EV[ev.type] and (ev.day or 0) >= day - cfg.amb_site_days and I and I.x and not A["ev" .. tostring(ev.id)] and (I.x - px) ^ 2 + (I.z - pz) ^ 2 < cfg.amb_site_r ^ 2 then
      A["ev" .. tostring(ev.id)] = true
      return "site", string.format(N.pick(N.AMB.site), ev.town_name or I.name or "this place")
    end
  end
  local T = rawget(_G, "KMM_Tempo")
  local TC = T and T.cfg or {}
  local dir, full = TC.hunger_dir or -1, TC.hunger_full or 300
  local dk = math.floor(day)
  if (A.hungry_day or -1) < dk then   -- голод: раз в игровой день
    local n = 0
    for _, pc in ipairs(L) do
      local okh, h = pcall(function() return pc:getMedical().hunger end)
      if okh and type(h) == "number" and h >= 0 and h <= 1.5 * full then
        if (dir < 0 and h < cfg.amb_hungry * full) or (dir > 0 and h > (1 - cfg.amb_hungry) * full) then n = n + 1 end
      end
    end
    if n * 2 >= #L and n > 0 then A.hungry_day = dk; return "hungry", N.pick(N.AMB.hungry) end
  end
  if N.cfg().scars then   -- шрам: живой свой вспоминает, где лежал (раз на шрам)
    local X2 = N.state(S)
    for _, pc in ipairs(L) do
      local okn, nm = pcall(function() return pc:getName() end)
      local sc = okn and nm and X2.scars and X2.scars[nm]
      if sc and day - sc.day >= cfg.scar_days then
        X2.scars[nm] = nil
        return "scar", string.format(N.pick(N.AMB.scar), sc.place), pc
      end
    end
  end
  if cfg.night then   -- ночь вне города: раз за ночь
    local okh, hh = pcall(function() return getGameWorld():getTimeStamp_inGameHours():getTotalHours() end)
    if okh and type(hh) == "number" then
      local h = hh % 24
      local nightk = math.floor((hh - cfg.night_to) / 24)   -- 22:00 дня d и 03:00 дня d+1 — одна ночь
      local okt, inT = pcall(function() return L[1]:getCurrentTownLocation() ~= nil end)
      if (h >= cfg.night_from or h < cfg.night_to) and okt and not inT and A.night_k ~= nightk then
        A.night_k = nightk
        return "night", N.pick(N.AMB.night)
      end
    end
  end
  local K = rawget(_G, "KMM_Stock")
  if K and K.stock then   -- город под ногами: осада / пустые прилавки, раз в 3 дня на город
    local okt, tsid = pcall(function() local t = L[1]:getCurrentTownLocation(); local gd = t and (t:getGameData() or t.data); return gd and gd.stringID end)
    if okt and tsid and dk - (A["t" .. tsid] or -1000) >= 3 then
      local okst, st = pcall(K.stock, tsid)
      local tn = (TI[tsid] and TI[tsid].name) or "this town"
      if okst and st and st.siege then A["t" .. tsid] = dk; return "siege", string.format(N.pick(N.AMB.siege), tn) end
      local okl, lv = pcall(K.level, tsid, "food")
      if okl and type(lv) == "number" and lv >= 0 and lv < cfg.amb_stock_low then A["t" .. tsid] = dk; return "empty", string.format(N.pick(N.AMB.empty), tn) end
    end
  end
  return nil
end
function N.scars(C, S, D)   -- опрос своих: упал/встал; шрам = место, где лежал
  local cfg = N.cfg()
  if not cfg.scars then return end
  local X = N.state(S)
  X.scars = X.scars or {}
  N.downs = N.downs or {}
  local day = N.day(C)
  local seen = {}
  pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local okn, nm = pcall(function() return pc:getName() end)
      local okd, dn = pcall(function() return pc:isDown() and not pc:isDead() end)
      if okn and nm and okd then
        seen[nm] = true
        local was = N.downs[nm]
        if dn and not was then
          local okp, p = pcall(function() return pc:getPosition() end)
          local t = okp and p and N.where(D, p.x, p.z)
          N.downs[nm] = { place = t and t.name or nil }
        elseif not dn and was then
          N.downs[nm] = nil
          if was.place then
            local n = 0; for _ in pairs(X.scars) do n = n + 1 end
            if n < cfg.scar_max then X.scars[nm] = { place = was.place, day = day } end
          end
          if os.clock() - (N.up_t or -1e9) > 60 and math.random() < cfg.scar_up_p then N.up_t = os.clock(); N.said[#N.said + 1] = { leader = pc, line = N.pick(N.AMB.up), t = os.clock() + 2, banter = true, amb = "up" } end
        end
      end
    end
  end)
  for nm in pairs(N.downs) do if not seen[nm] then N.downs[nm] = nil end end
end
function N.ambient(C, S)
  local cfg = N.cfg()
  if not cfg.ambient or N.amb_off then return end
  local now = os.clock()
  if now - (N.amb_t or -1e9) < cfg.amb_gap_s or now - (N.banter_t or -1e9) < cfg.amb_after_banter_s then return end
  N.amb_t = now - cfg.amb_gap_s + 30   -- повтор проверки через 30 с, если сказать нечего
  local L = N.squad_alive()
  if #L == 0 then return end
  local k, line, who = N.ambient_line(C, S, L)
  if not line then return end
  N.amb_t = now
  N.said[#N.said + 1] = { leader = who or L[math.random(#L)], line = line, t = now + 1, banter = true, amb = k }
end
function N.banter(typ, deed)   -- свой из отряда отзывается о деле; говорит не тот, кого назвали в событии, — любой живой рядом
  local cfg = N.cfg()
  local L = N.BANTER[typ]
  local TL = cfg.traits and typ and true
  if not (cfg.banter and (L or TL)) or math.random() >= cfg.banter_p then return end
  local now = os.clock()
  if now - (N.banter_t or -1e9) < cfg.banter_gap_s then return end
  local pick, n, tp, tn, tline = nil, 0, nil, 0, nil
  pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local okd, dn = pcall(function() return pc:isDead() or pc:isDown() end)
      if okd and not dn then
        n = n + 1; if math.random(1, n) == 1 then pick = pc end   -- равновероятный выбор без списка
        if cfg.traits then
          local okn, nm = pcall(function() return pc:getName() end)
          local tr = okn and N.trait_of(nm)
          local tl = tr and (deed and N.TRAITS[tr][typ .. "_" .. deed] or N.TRAITS[tr][typ])
          if tl then tn = tn + 1; if math.random(1, tn) == 1 then tp, tline = pc, N.pick(tl) end end
        end
      end
    end
  end)
  local line
  if tp and (not L or math.random() < cfg.trait_p) then pick, line = tp, tline
  elseif L then line = N.pick(L) end
  if not (pick and line) then return end
  N.banter_t = now
  N.said[#N.said + 1] = { leader = pick, line = line, t = now + cfg.banter_delay_s, banter = true, trait = tp == pick or nil }
end

-- учёт ударов игрока --------------------------------------------------------------------------------------------------------
function N.on_player_hit(victim, attacker)
  if N.off then return end
  local ok, err = pcall(function()
    local okn, nm = pcall(function() return victim:getName() end)
    local okf, fid = pcall(function() local f = victim:getFaction(); local gd = f and (f:getData() or f.data); return gd and gd.stringID end)
    if not (okn and nm and okf and fid) then return end
    local key = tostring(fid) .. "|" .. tostring(nm)
    local c = N.cand[key]
    local now = os.clock()
    if not c then
      local nc = 0; for _ in pairs(N.cand) do nc = nc + 1 end
      if nc >= 40 then return end
      local okl, lead = pcall(function() local pl = victim:getPlatoon(); return pl and pl:getSquadLeader() == victim end)
      local okp, p = pcall(function() return victim:getPosition() end)
      c = { ch = victim, n = nm, fid = fid, first = now, hits = 0, lead = okl and lead == true, x = okp and p and p.x, z = okp and p and p.z,
            pn = nil }
      local oka, an = pcall(function() return attacker:getName() end)
      c.pn = oka and an or nil
      local oks, sid = pcall(function() local gd = victim:getGameData(); return gd and gd.stringID end)
      c.sid = oks and sid or nil
      N.cand[key] = c
    end
    c.hits = c.hits + 1
    c.last = now
  end)
  if not ok then N.fail("on_player_hit", err) end
end

-- именные охотники за головой ------------------------------------------------------------------------------------------------
function N.hunters(S) local X = N.state(S); X.hunters = X.hunters or {}; return X.hunters end
function N.hunter_name() return N.pick(N.SYL_A) .. N.pick(N.SYL_B) .. " " .. N.pick(N.HT) end
function N.hunter_key(S, name)
  for fid, h in pairs(N.hunters(S)) do if h.n == name then return fid end end
  return nil
end
function N.hunt_bonus(hfid)   -- зовёт KMM_Traces перед выбором тира охоты
  if N.off or not N.cfg().hunters then return 0 end
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state()
  local h = S and N.hunters(S)[hfid]
  return h and math.min(N.cfg().hunter_max_bonus, h.wins or 0) or 0
end
function N.on_hunt(pl, hfid, client, amount)   -- зовёт KMM_Traces: отряд охотников заспавнен
  if N.off or not N.cfg().hunters then return end
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state()
  if not S then return end
  local H = N.hunters(S)
  local day = N.day(C)
  local h = H[hfid]
  if not h then h = { n = N.hunter_name(), fid = hfid, met = 0, wins = 0, day = day }; H[hfid] = h end
  local okl, leader = pcall(function() return pl:getSquadLeader() end)
  if not (okl and leader) then return end
  pcall(function() leader:setName(h.n) end)
  local line, hev
  if h.met == 0 and h.heir_of then line = string.format(N.pick(N.SAY.hunt_heir), h.heir_of)
  elseif (h.wins or 0) > 0 and h.place then line = string.format(N.pick(N.SAY.hunt_again), h.place)
  else line = string.format(N.pick(N.SAY.hunt_first), math.floor(tonumber(amount) or 0)); hev = "EV_BOUNTY_SPOTTED" end   -- общий повод — ванильная реплика
  h.met = h.met + 1; h.last = day
  N.said[#N.said + 1] = { leader = leader, line = line, t = os.clock() + N.cfg().say_delay_s, ev = hev }
  if (h.wins or 0) > 0 then N.remember(leader, "LT_DEFEATED_MY_SQUAD_ONCE") end
  local okn, fname = pcall(C.name, hfid)
  N.emit(C, nil, "nemesis_hunter", string.format("%s, hunter of %s, is on the trail of the Nameless again.", h.n, okn and fname or hfid),
         { leader_name = h.n, a = hfid, b = client, met = h.met, amount = amount })
end
function N.hunter_cand(C, S, D, hk, key, c, dead, near, down_now)   -- исход боя с именным охотником
  local cfg = N.cfg()
  local H = N.hunters(S)
  local h = H[hk]
  local now = os.clock()
  if dead then
    N.cand[key] = nil
    local heir = { n = N.hunter_name(), fid = hk, met = 0, wins = 0, day = N.day(C), heir_of = h.n }
    H[hk] = heir
    local X = N.state(S); X.hunters_dead = (X.hunters_dead or 0) + 1
    N.emit(C, nil, "nemesis_hunter_dead", string.format("The bounty hunter %s was killed by the Nameless. %s takes up the warrant.", h.n, heir.n),
           { leader_name = h.n, a = hk, heir = heir.n })
  elseif now - (c.last or c.first) > cfg.linger_s and not (near and down_now) then
    N.cand[key] = nil
    if c.hits >= cfg.min_hits and c.down then
      local t, rg = N.where(D, c.x, c.z)
      h.wins = (h.wins or 0) + 1; h.place = (t and t.name) or rg or h.place
      N.emit(C, nil, "nemesis_hunter_beaten", string.format("The bounty hunter %s was beaten by the Nameless near %s and swears to collect.", h.n, h.place or "the road"),
             { leader_name = h.n, a = hk, wins = h.wins, x = c.x, z = c.z })
    end
  end
end

-- исход боя -------------------------------------------------------------------------------------------------------------------
function N.resolve(M, O, D, C, S)
  local cfg = N.cfg()
  local now = os.clock()
  local px, pz = N.player_pos()
  for key, c in pairs(N.cand) do
    -- к персонажу обращаемся, только пока игрок рядом (он точно загружен); ушёл игрок — решаем по уже известному
    local near = px and c.x and ((px - c.x) ^ 2 + (pz - c.z) ^ 2) < cfg.near_r ^ 2 and now - c.first < cfg.max_wait_s
    local dead, down_now = false, false
    if near then
      local okd, d = pcall(function() return c.ch:isDead() end)
      local okw, w = pcall(function() return c.ch:isDown() end)
      dead = okd and d == true
      down_now = okw and w == true
      if down_now then c.down = true end
    end
    if dead and C.leader_fell and N.cfg().leaders ~= false then local okl, lev = pcall(C.leader_fell, c.sid, c.n, "killed", true); if okl and lev then N.log("leader_fell: " .. tostring(lev.text)); N.banter("leader_fell"); N.deed_add(C, "leader_fell", lev.leader_name, c.x, c.z); N.count(S, "leaders") end end   -- лидер города: модель мира узнаёт
    local hk = N.cfg().hunters and N.hunter_key(S, c.n)
    if hk then N.hunter_cand(C, S, D, hk, key, c, dead, near, down_now)
    elseif dead then
      N.cand[key] = nil
      local r = O and N.find(O, c.n)
      if r then
        M.die(C, O, D, M.cfg(), r, N.day(C), "was cut down by the Nameless")   -- через KMM_Outlaws: замена в очередь + N.on_dead
      elseif N.gone and N.gone[c.n] then
        N.gone[c.n] = nil
      elseif c.hits >= cfg.min_hits and math.random() < cfg.avenger_p * (c.lead and cfg.leader_mult or 1) then
        N.make(M, O, D, C, S, c, "avenger")
      end
    elseif now - (c.last or c.first) > cfg.linger_s and not (near and down_now) then   -- лежит рядом с игроком — ещё не решено
      N.cand[key] = nil
      if c.hits >= cfg.min_hits or c.beat then
        if c.down then N.count(S, "spared") end
        local r = O and N.find(O, c.n)
        -- исход: уложил его игрок -> spared; стоял, а свой игрока лёг от его руки или руки его банды -> beat (обратная память);
        -- свой игрока ложился от кого-то ещё -> без соперника (не «сбежал»); никто из своих не ложился -> fled
        local deed = c.down and "spared" or (c.beat and "beat") or (not c.plost and "fled") or nil
        if r and deed == "beat" then N.beat_again(C, r, c)
        elseif r then N.again(M, O, D, C, S, r, c)   -- пережил встречу с игроком снова (как раньше)
        elseif deed then
          local p = (deed == "spared" and cfg.rival_p_spared or deed == "beat" and cfg.rival_p_beat or cfg.rival_p_fled) * (c.lead and cfg.leader_mult or 1)
          if N.poor(C) then p = p * cfg.weak_rival_mult end   -- слабый нищий игрок: спираль соперников медленнее
          if math.random() < p then N.make(M, O, D, C, S, c, deed) end
        end
      end
    end
  end
end
function N.make(M, O, D, C, S, c, deed)
  local cfg = N.cfg()
  local X = N.state(S)
  local day = N.day(C)
  local maxr = cfg.max_rivals
  if N.poor(C) then maxr = math.min(maxr, cfg.weak_max_rivals) end   -- слабый нищий игрок: не больше weak_max_rivals живых соперников
  if #N.rivals(O) >= maxr or day - X.last_new < cfg.cooldown_days then
    N.log(string.format("nemesis_skip: %s deed=%s rivals=%d/%d", tostring(c.n), tostring(deed), #N.rivals(O), maxr))
    return nil
  end
  local t, rg = N.where(D, c.x, c.z)
  if not rg then return nil end
  local gang = (D.gangs and D.gangs[c.fid]) and c.fid or nil
  local o = M.born(C, O, D, day, rg, gang)
  if not o then return nil end
  local base, gen = N.base_name(c.n)
  local place = (t and t.name) or rg
  if deed == "avenger" then
    o.n = N.pick(N.SYL_A) .. N.pick(N.SYL_B) .. " Oathsworn"
  else
    o.n = base .. " " .. N.pick(N.EPI[deed])
  end
  o.ek = "grudge"   -- прозвище уже заслужено встречей с игроком
  o.pg = { deed = deed, place = place, day = day, base = (deed == "avenger") and nil or c.n, dead = (deed == "avenger") and c.n or nil,
           gen = gen, met = 1, pn = c.pn }
  o.t = math.max(o.t, c.lead and 1 or 0)
  X.last_new = day; X.born = X.born + 1
  local txt
  if deed == "avenger" then
    txt = string.format("%s has sworn on the grave of %s to find the Nameless who killed him near %s.", o.n, c.n, place)
  elseif deed == "spared" then
    txt = string.format("%s was left for dead by the Nameless near %s. He got up. Now he asks about them in every bar.", o.n, place)
  elseif deed == "escaped" then
    txt = string.format("%s broke the chains the Nameless put on him near %s. He has not forgotten the collar.", o.n, place)
  elseif deed == "beat" then
    txt = string.format("%s beat the Nameless into the dirt near %s and walked off laughing. He tells it in every bar.", o.n, place)
  else
    txt = string.format("%s fled from the Nameless near %s and swore it was the last time. He is gathering a crew.", o.n, place)
  end
  N.emit(C, o, "nemesis_born", txt, { deed = deed, place = place, x = c.x, z = c.z })
  return o
end
function N.beat_again(C, r, c)   -- соперник снова уложил игрока: ещё строка в его легенде (без роста тира — он и так сильнее)
  r.pg.won = (r.pg.won or 0) + 1
  local _, _, D = N.outlaws()
  local t, rg = N.where(D, c.x, c.z)
  r.pg.wplace = (t and t.name) or rg or r.pg.wplace
  N.emit(C, r, "nemesis_beat_again", string.format("%s beat the Nameless again near %s. He has lost count of how many times.", r.n, r.pg.wplace or "the road"),
         { won = r.pg.won, x = c.x, z = c.z })
end
-- ОБРАТНАЯ ПАМЯТЬ «кто тебя уложил»: свой игрока был на ногах и лёг -> победитель из ванильного Character.lastGuyWhoDefeatedMe (hand).
-- Победитель жив, не игрок и не дальше beat_win_r от уложенного (поле хранит последнего победителя, поэтому только переход «стоял -> лёг»).
-- Он и его банда (та же фракция, рядом) в кандидатах: c.beat; кандидата нет (игрок не бил его min_hits раз) — заводится. Любой лёгший свой
-- помечает всех кандидатов рядом c.plost: «сбежал от Безымянных» для них уже неправда.
function N.beat_scan(C, S)
  local cfg = N.cfg()
  local now = os.clock()
  local bt = N.beat_t or -1e9
  if now >= bt and now - bt < cfg.beat_scan_s then return end
  N.beat_t = now
  if N.pcup_S ~= S then N.pcup_S, N.pcup = S, {} end
  local up = N.pcup
  local seen = {}
  for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
    local okk, k = pcall(function() return pc:getHandle():toString() end)
    if not (okk and type(k) == "string") then local okn, nm = pcall(function() return pc:getName() end); k = okn and nm or nil end
    if k then
      seen[k] = true
      local okd, dn = pcall(function() return pc:isDead() or pc:isDown() or pc:isUnconcious() end)
      if okd and not dn then up[k] = true
      elseif okd and dn and up[k] then
        up[k] = nil
        local okp, px, pz = pcall(function() local p = pc:getPosition(); return p.x, p.z end)
        if okp and px then N.player_lost(pc, px, pz, now) end
      end
    end
  end
  for k in pairs(up) do if not seen[k] then up[k] = nil end end
end
function N.player_lost(pc, px, pz, now)
  local cfg = N.cfg()
  local okw, w = pcall(function() local hd = pc.lastGuyWhoDefeatedMe; return hd and hd:getCharacter() end)
  if not okw then w = nil end
  local okh, hko = pcall(function() return pc:getMedical():isHungerKO() end)   -- лёг от голода — поле хранит старого победителя
  if okh and hko == true then w = nil end
  local wn, wf, wx, wz
  if w then
    local okv, ok2 = pcall(function()
      if w:isDead() or w:isPlayerCharacter() then return false end
      local p = w:getPosition()
      if not p or (p.x - px) ^ 2 + (p.z - pz) ^ 2 > cfg.beat_win_r ^ 2 then return false end
      wx, wz = p.x, p.z
      wn = w:getName()
      local f = w:getFaction(); local gd = f and (f:getData() or f.data); wf = gd and gd.stringID
      return wn ~= nil and wf ~= nil
    end)
    if not (okv and ok2) then wn, wf = nil, nil end
    if wn then   -- свежесть: победитель сейчас в бою (isInCombatMode) или только что дрался с игроком (кандидат с ударом не старше linger_s)
      local okc, inc = pcall(function() return w:isInCombatMode(true, true) end)
      local c0 = N.cand[tostring(wf) .. "|" .. tostring(wn)]
      local fought = c0 and c0.hits > 0 and now - (c0.last or c0.first) <= cfg.linger_s
      if not (fought or (okc and inc == true)) then
        N.log(string.format("beaten: stale winner %s (not fighting, no fresh hits) - no rival", tostring(wn)))
        wn, wf = nil, nil
      end
    end
  end
  local pname = "?"; pcall(function() pname = tostring(pc:getName()) end)
  for _, c in pairs(N.cand) do
    if c.x and (c.x - px) ^ 2 + (c.z - pz) ^ 2 < cfg.near_r ^ 2 then
      c.plost = true
      if wf and c.fid == wf then c.beat = true; c.last = now end
    end
  end
  if not wn then N.log(string.format("beaten: %s went down, winner unknown or gone - no rival from this", pname)); return end
  local key = tostring(wf) .. "|" .. tostring(wn)
  local c = N.cand[key]
  if not c then
    local nc = 0; for _ in pairs(N.cand) do nc = nc + 1 end
    if nc >= 40 then return end
    local okl, lead = pcall(function() local pl = w:getPlatoon(); return pl and pl:getSquadLeader() == w end)
    local oks, sid = pcall(function() local gd = w:getGameData(); return gd and gd.stringID end)
    c = { ch = w, n = wn, fid = wf, first = now, hits = 0, lead = okl and lead == true, x = wx, z = wz, pn = pname, sid = oks and sid or nil }
    N.cand[key] = c
  end
  c.beat, c.plost, c.last = true, true, now
  N.log(string.format("beaten: %s went down to %s (%s)%s", pname, wn, wf, c.lead and " leader" or ""))
end
function N.again(M, O, D, C, S, r, c)   -- снова уложен и снова оставлен жить: растёт
  r.pg.met = (r.pg.met or 1) + 1
  r.t = math.min(3, r.t + 1)
  r.b = r.b + 1500
  if r.pg.met == 2 then
    r.pg.aka = r.pg.aka or {}
    r.pg.aka[#r.pg.aka + 1] = r.n
    r.n = r.n:match("^(%S+)") .. " " .. N.pick(N.EPI.again)
    local lv = M.live and M.live["o" .. r.i]   -- живой отряд рядом: главаря переименовать сразу (иначе KMM_Outlaws сочтёт его погибшим)
    if lv and lv.pl then pcall(function() lv.pl:getSquadLeader():setName(r.n) end) end
  end
  N.emit(C, r, "nemesis_again", string.format("%s survived the Nameless again. They say he only gets angrier.", r.n), { met = r.pg.met })
  if r.pg.met >= N.cfg().warlord_met and not r.pg.warlord and r.g and C.warlord_from and N.cfg().warlords then   -- вырос в варлорда
    local okw, w = pcall(C.warlord_from, r.g, r.n)
    if okw and w then r.pg.warlord = w; N.log("nemesis_warlord: " .. r.n .. " -> " .. tostring(w)) end
  end
end

-- преследование (раз в игровой день) ----------------------------------------------------------------------------------------
function N.co_day(M, O, D, C, S, day)   -- компания-соперник: появление, перехват награды, встреча
  local cfg = N.cfg()
  if not cfg.company then return end
  local X = N.state(S)
  local rivals = N.rivals(O)
  if not X.co then
    if #rivals == 0 and not X.title then return end   -- игрок ещё не заметен
    local fid
    for _, want in ipairs(cfg.co_factions) do
      for f in pairs(S.F) do
        local okn, nm = pcall(C.name, f)
        if okn and nm == want and M.tier_sid(D, f, 1) and not fid then fid = f end
      end
    end
    if not fid then return end
    X.co = { n = N.pick(N.CO_NAMES), cap = N.pick(N.SYL_A) .. N.pick(N.SYL_B), fid = fid, kills = 0, met = 0, day = day }
    N.emit(C, nil, "nemesis_company", string.format("%s, a crew of %s under %s, has taken an interest in the same bounties as the Nameless.",
           X.co.n, C.name(fid), X.co.cap), { leader_name = X.co.cap, a = fid })
    return
  end
  local co = X.co
  for _, r in ipairs(rivals) do   -- перехват: не больше одного в день
    if math.random() < cfg.co_steal_p then
      co.kills = co.kills + 1; co.last_kill = r.n
      local nm = r.n
      pcall(M.die, C, O, D, M.cfg(), r, day, "was hunted down by " .. co.n)
      N.emit(C, nil, "nemesis_co_kill", string.format("%s of %s collected the bounty on %s before the Nameless could.", co.cap, co.n, nm),
             { leader_name = co.cap, a = co.fid, victim = nm })
      break
    end
  end
  if day - (co.last_meet or -1000) >= cfg.co_meet_days and math.random() < cfg.co_meet_p then
    local T = rawget(_G, "KMM_Traces")
    local px, pz = N.player_pos()
    local sid = M.tier_sid(D, co.fid, 1)
    if T and T.request and px and sid then
      local a = math.random() * 6.2832
      local line, co_ev
      if co.last_kill and not co.told_kill then line = string.format(N.pick(N.SAY.co_kill), co.last_kill)
      elseif X.title then line = string.format(N.pick(N.SAY.co_title), X.title)
      else line = N.pick(N.SAY.co_plain); co_ev = "EV_I_SEE_NEUTRAL_SQUAD" end   -- безымянная встреча — ванильная реплика
      local job = { tag = "company", fid = co.fid, sid = sid, n = 1, size = 4, from_x = px + math.cos(a) * 2000, from_z = pz + math.sin(a) * 2000, to_x = px, to_z = pz,
                    on_spawn = function(pls)
                      local pl = pls and pls[1]
                      local okl, leader = pcall(function() return pl:getSquadLeader() end)
                      if not (okl and leader) then return end
                      pcall(function() leader:setName(co.cap) end)
                      pcall(function() pl:getActivePlatoon():setName(co.n) end)
                      N.said[#N.said + 1] = { leader = leader, line = line, t = os.clock() + cfg.say_delay_s, ev = co_ev }
                      if co.last_kill then co.told_kill = true end
                    end }
      local okq, acc = pcall(T.request, job)
      if okq and acc then co.last_meet = day; co.met = co.met + 1 end
    end
  end
end
function N.day_step(M, O, D, C, S, day)
  local cfg = N.cfg()
  local px, pz = N.player_pos()
  local _, prg = N.where(D, px, pz)
  for _, o in ipairs(N.rivals(O)) do
    o.b = o.b + cfg.bounty_day
    if day - (o.pg.grown or o.pg.day) >= cfg.grow_days and o.t < 3 then o.t = o.t + 1; o.pg.grown = day end
    if o.pk then   -- S3: постоянный отряд с пакетом охоты идёт за игроком сам (ядро); регион — по его настоящей позиции
      local _, org = N.where(D, o.x, o.z)
      if org and org ~= o.r and D.regions[org] then
        o.r = org
        o.pg.trail = (o.pg.trail or 0) + 1
        if org == prg then N.emit(C, o, "nemesis_trail", string.format("%s was seen in %s, asking after the Nameless.", o.n, org)) end
      end
    elseif prg and o.r ~= prg and D.regions[prg] and math.random() < cfg.follow_p then   -- идёт по следу игрока
      o.hr, o.r = prg, prg
      o.x, o.z, o.s = M.spot(D, prg)
      o.pg.trail = (o.pg.trail or 0) + 1
      if o.pg.trail == 1 or math.random() < 0.2 then
        N.emit(C, o, "nemesis_trail", string.format("%s was seen in %s, asking after the Nameless.", o.n, prg))
      end
    end
  end
end

-- гибель соперника (зовёт KMM_Outlaws.die): слух и запрет мстителя за самого соперника
function N.on_dead(o, how)
  if not (o and o.pg) then return end
  N.gone = N.gone or {}
  N.gone[o.n] = true
  for _, a in ipairs(o.pg.aka or {}) do N.gone[a] = true end
  local C = rawget(_G, "KMM_Conductor")
  if not C then return end
  local S = C.state(); if S then local X = N.state(S); X.dead = X.dead + 1 end
  local byp = false
  for _, c in pairs(N.cand) do if c.n == o.n then byp = true end end
  local txt = byp and string.format("%s finally fell to the Nameless. The grudge is buried with him.", o.n)
              or string.format("%s is dead (%s). He never settled his score with the Nameless.", o.n, tostring(how or "killed"))
  N.emit(C, o, "nemesis_dead", txt, { status = "dead", by_player = byp })
end

-- встреча: реплика главаря (зовёт KMM_Outlaws.vis после спавна) ----------------------------------------------------------------
function N.on_spawn(o, leader)
  if N.off or not (o and o.pg and leader) then return end
  local C = rawget(_G, "KMM_Conductor")
  local deed = o.pg.deed
  local pool = (o.pg.met or 1) >= 2 and N.SAY.again or N.SAY[deed] or N.SAY.spared
  local line = string.format(N.pick(pool), deed == "avenger" and (o.pg.dead or "him") or (o.pg.place or "the road"))
  local met = o.pg.met or 1
  local sev = (o.pg.told == met) and "EV_I_SEE_ENEMY_PLAYER" or nil   -- о новом деле — наша строка один раз, дальше ванильная реплика врага
  o.pg.told = met
  N.said[#N.said + 1] = { leader = leader, line = line, t = os.clock() + N.cfg().say_delay_s, ev = sev }
  N.remember(leader, deed == "avenger" and "LT_KILLED_MY_FRIEND" or deed == "escaped" and "LT_MY_CAPTOR" or deed == "beat" and "LT_SQUAD_LOST_TO_ME_ONCE"
             or "LT_DEFEATED_MY_SQUAD_ONCE")   -- родная память ядра (beat: «его отряд мне проиграл»)
  if C then
    local S = C.state(); if S then local X = N.state(S); X.met = X.met + 1 end
    N.emit(C, o, "nemesis_return", string.format("%s has caught up with the Nameless.", o.n))
  end
  if N.cfg().appraise ~= false and not N.appr_off and o.i and C then   -- Y5: оценка, когда подойдёт (в такте)
    local okS, S = pcall(C.state)
    if not okS then S = nil end
    if N.appr_S ~= S or not N.appr then N.appr_S = S; N.appr = {} end
    N.appr["o" .. o.i] = { o = o, leader = leader, t0 = os.clock() }
  end
end

-- Y5: оценка видимой силы игрока при встрече -----------------------------------------------------------------------------------
-- Поля ядра (✓код): StateBroadcastData.apparentStrength/actualStrength (StateBroadcastData.h), Blackboard.moraleIsBroken (Blackboard.h),
-- SensoryData canISeeThisGuy (SensoryData.h). Шкала силы ? — сравнивается только отношение. Пишем лишь ванильный пакет миссии S3.
function N.appr_read(leader, cfg)   -- таблица оценки или nil, причина
  local okp, lp = pcall(function() local p = leader:getPosition(); return { x = p.x, z = p.z } end)
  if not (okp and lp) then return nil, "no leader position" end
  local okS, sens = pcall(function() return leader:getSensoryData() end)
  if not okS then sens = nil end
  local A = { app = 0, seen = 0, down = 0, hid = 0, near = false, broken = false }
  local okL, eL = pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local okq, q = pcall(function() local p = pc:getPosition(); return { x = p.x, z = p.z } end)
      local d2 = okq and q and ((q.x - lp.x) ^ 2 + (q.z - lp.z) ^ 2)
      if d2 and d2 < cfg.appr_seen_r ^ 2 then
        if d2 < cfg.appr_r ^ 2 then A.near = true end
        local okd, dn = pcall(function() return pc:isDead() or pc:isDown() end)
        if okd and dn then A.down = A.down + 1   -- лежачий в силу не входит: видно, что отряд побит
        else
          local okv, vis = true, true
          if sens then okv, vis = pcall(function() return sens:canISeeThisGuy(pc) end) end
          if not okv then vis = true end   -- чувства не прочитались — по расстоянию
          if vis then
            A.vis = (A.vis or 0) + 1
            local oka, a = pcall(function() return pc:getStateBroadcast().apparentStrength end)
            if oka and type(a) == "number" and a >= 0 then A.app = A.app + a; A.seen = A.seen + 1 end
            local okb, b = pcall(function() return pc:getBlackboard().moraleIsBroken end)
            if okb and b == true then A.broken = true end
          else A.hid = A.hid + 1 end
        end
      end
    end
  end)
  if not okL then return nil, "player squad: " .. tostring(eL) end
  local oks, act, app = pcall(function() local sb = leader:getStateBroadcast(); return sb.actualStrength, sb.apparentStrength end)
  local own = oks and ((type(act) == "number" and act > 0 and act) or (type(app) == "number" and app > 0 and app)) or nil
  if not own then return nil, "no own strength" end
  local okz, size = pcall(function() return leader:getPlatoon():getSquadSize() end)
  A.size = (okz and type(size) == "number" and size >= 1) and size or 1
  A.own = own * A.size
  local okm, rb = pcall(function() return leader:getBlackboard().moraleIsBroken end)
  A.rbroken = okm and rb == true
  A.ratio = A.app * (A.broken and cfg.appr_broken or 1) / A.own
  return A
end
function N.appr_decide(A, cfg)
  if A.rbroken then return "withdraw" end   -- у самой банды дух сломлен
  if A.poor and A.ratio < cfg.appr_attack and cfg.appr_contempt ~= false then return "contempt" end   -- слаб и взять нечего
  if A.ratio < cfg.appr_attack then return "attack" end
  if A.ratio >= cfg.appr_flee then return "withdraw" end
  return "parley"
end
function N.appr_pkg(o, board_fn, kind)   -- ванильный пакет S3 (pkg_hunt / pkg_roam из cfg KMM_Outlaws) на доску отряда; true — поставлен
  local OM = rawget(_G, "KMM_Outlaws")
  local M = OM and OM._M
  if not (M and M.cfg) then return false end
  local mc = M.cfg()
  if mc.pkg == false then return false end
  local sid, gd = mc["pkg_" .. kind], nil
  if sid then pcall(function() gd = getGameWorld().gamedata:getData(sid, (itemType and itemType.AI_PACKAGE) or 72) end) end
  local okb, board = pcall(board_fn)
  if not (gd and okb and board) then N.log(string.format("appraise: package FAIL %s on %s: %s", kind, tostring(o.n), gd and "no blackboard" or "no AI_PACKAGE data")); return false end
  local call = function() board:replaceAIPackage(gd) end
  local ok
  if M.probe_call then ok = M.probe_call("ai_package", call) else ok = pcall(call) end
  N.log(string.format("appraise: package %s %s on %s", ok and "ok" or "FAIL", kind, tostring(o.n)))
  return ok
end
function N.appr_act(C, S, e, A, dec, cfg)
  local o, leader, now = e.o, e.leader, os.clock()
  local board_fn = function() return leader:getBlackboard() end
  N.appr_n = N.appr_n or {}
  N.appr_n[dec] = (N.appr_n[dec] or 0) + 1
  if dec == "attack" then
    if e.roam then N.appr_pkg(o, board_fn, "hunt") end   -- после угрозы пакет был «бродить» — снова охота
    if e.roam or A.broken then N.said[#N.said + 1] = { leader = leader, line = N.pick(N.SAY.appr_attack), t = now + 1, ev = "EV_LAUNCH_ATTACK" } end
  elseif dec == "contempt" then   -- взять нечего: «бродить», реплика; регрупп (wd_day) вернёт охоту, следующая встреча — новая оценка
    if not e.roam then N.appr_pkg(o, board_fn, "roam") end
    N.said[#N.said + 1] = { leader = leader, line = N.pick(N.SAY.appr_contempt), t = now + 1 }
    local today = N.day(C)
    if o.pg then o.pg.wd_day = today end
    if o.pg and o.pg.ctd and today - o.pg.ctd < cfg.appr_contempt_days then
      N.appr_n.ct_dup = (N.appr_n.ct_dup or 0) + 1
    else
      if o.pg then o.pg.ctd = today; o.pg.ct = (o.pg.ct or 0) + 1 end
      N.emit(C, o, "nemesis_contempt", string.format("%s found the Nameless with empty pockets and let them crawl away. He says he will come back when they are worth robbing.", o.n),
             { app = A.app, own = A.own })
    end
  elseif dec == "parley" then
    e.roam = N.appr_pkg(o, board_fn, "roam") or e.roam   -- остановить штурм: дальше решает ванильный ИИ, мы пересмотрим
    e.phase, e.tp = "parley", now + cfg.appr_parley_s
    N.said[#N.said + 1] = { leader = leader, line = N.pick(N.SAY.appr_parley), t = now + 1 }
  else
    if not e.roam then N.appr_pkg(o, board_fn, "roam") end
    N.said[#N.said + 1] = { leader = leader, line = N.pick(N.SAY.appr_withdraw), t = now + 1, ev = "EV_GIVE_UP_CHASE" }
    local today = N.day(C)
    if o.pg then o.pg.wd_day = today end
    if o.pg and o.pg.wdd and today - o.pg.wdd < cfg.appr_withdraw_days then   -- тот же отход (новый спавн того же героя): без события и счёта
      N.appr_n.wd_dup = (N.appr_n.wd_dup or 0) + 1
      N.log(string.format("appraise: withdraw repeat of %s within %d days - no new event", tostring(o.n), cfg.appr_withdraw_days))
    else
      if o.pg then o.pg.wdd = today; o.pg.wd = (o.pg.wd or 0) + 1 end
      N.emit(C, o, "nemesis_withdrew", string.format("%s sized up the Nameless and backed off. He will be back.", o.n), { app = A.app, own = A.own })
    end
  end
end
-- Отход соперника был недавно (не старше days, по умолчанию appr_withdraw_days игровых дней): для KMM_Outlaws.vis - не слать новый отряд
-- охоты сразу после отхода. x: запись соперника (таблица), её номер i, ключ "o<i>" или имя/прозвище.
function N.withdrew_recent(x, days)
  local o = type(x) == "table" and x or nil
  if not o then
    local M, O = N.outlaws()
    if not (M and O and O.L) then return false end
    local key = type(x) == "number" and ("o" .. x) or tostring(x)
    o = O.L[key] or N.find(O, key)
  end
  local wdd = o and o.pg and o.pg.wdd
  if type(wdd) ~= "number" then return false end
  local C = rawget(_G, "KMM_Conductor")
  local d = N.day(C)
  return d >= wdd and d - wdd < (days or N.cfg().appr_withdraw_days)
end
-- Оценка выключилась (ошибка, нет проверки указателя): кому уже поставили «бродить», ставится метка регруппа, и охота
-- возвращается сразу (N.regroup_now), а не через appr_regroup_days, - постоянный соперник не останется бродить навсегда.
function N.appr_stop(C, why)
  for _, e in pairs(N.appr or {}) do
    if e.roam and e.o and e.o.pg then e.o.pg.wd_day = e.o.pg.wd_day or N.day(C) end
  end
  N.appr, N.appr_off, N.regroup_now = {}, true, true
  N.log(why)
end
-- Главарь ещё в живом наборе движка: getCharacterUpdateList и has — хеш по указателю без разыменования (ContainersReference ✓код;
-- тот же приём, что у снимка KMM_Gov: удалённый движком персонаж роняет игру, pcall не спасает). nil — проверить нечем.
function N.appr_live(ch)
  local ok, live = pcall(function() local set = getGameWorld():getCharacterUpdateList(); return set:has(ch) end)
  if not ok or type(live) ~= "boolean" then return nil end
  return live
end
function N.appr_drop(C, key, e, why)   -- снять оценку; после угрозы (пакет «бродить») — регрупп вернёт охоту
  N.appr[key] = nil
  if e.roam and e.o and e.o.pg then e.o.pg.wd_day = N.day(C) end
  N.log(string.format("appraise: %s dropped (%s)", tostring(e.o and e.o.n), why))
end
function N.appraise_step(C, S)
  local cfg = N.cfg()
  if N.appr_S ~= S then N.appr_S = S; N.appr = {} end   -- другой сейв: указатели прошлого мира не трогаем
  local now = os.clock()
  for key, e in pairs(N.appr or {}) do
    local live = N.appr_live(e.leader)
    if live == nil then   -- без проверки указателя не трогаем вовсе: как раньше
      N.appr_stop(C, "appraise: off until restart - no liveness check (getCharacterUpdateList has unavailable), behaviour as before")
      return
    end
    local okd, gone = false, nil
    if live then okd, gone = pcall(function() return e.leader:isDead() or e.leader:isDown() end) end
    if not live then N.appr_drop(C, key, e, "leader unloaded")
    elseif not okd or gone or not (e.o and e.o.st == "a") then
      N.appr_drop(C, key, e, (not okd and "leader unreadable") or (gone and "leader down or dead") or "rival record closed")
    elseif not e.phase or now >= e.tp then
      local A, why = N.appr_read(e.leader, cfg)
      if A and (A.vis or 0) > 0 and A.seen == 0 then A, why = nil, "apparentStrength unreadable" end
      local ready = A and A.near and (A.seen > 0 or (A.down > 0 and A.hid == 0))   -- видит своих игрока или все они лежат
      if (not A and why == "apparentStrength unreadable") and not e.phase then
        N.appr[key] = nil
        N.appr_n = N.appr_n or {}; N.appr_n.fallback = (N.appr_n.fallback or 0) + 1
        N.log(string.format("appraise: fallback %s: %s - assault package as before", tostring(e.o.n), why))
      elseif ready or e.phase == "parley" then
        local dec
        if A then
          if cfg.appr_contempt ~= false and e.o.pg and e.o.pg.deed ~= "avenger" then   -- мститель пришёл за кровью, не за добычей
            local okw, W = pcall(N.worth, C)
            if okw and type(W) == "table" then A.poor, A.wtxt = W.poor == true, W.txt end
          end
          dec = N.appr_decide(A, cfg)
          if e.phase == "parley" and dec == "parley" then   -- после угрозы середины нет: чем ближе к слабости, тем вероятнее штурм
            dec = math.random() < (cfg.appr_flee - A.ratio) / math.max(0.01, cfg.appr_flee - cfg.appr_attack) and "attack" or "withdraw"
          end
          if e.phase == "parley" and not A.near and A.seen == 0 then dec = "withdraw" end   -- разошлись
          N.log(string.format("appraise: app=%.1f own=%.1f (x%d) ratio=%.2f seen=%d hidden=%d down=%d broken=%s rbroken=%s -> %s (%s%s)%s",
                A.app, A.own, A.size, A.ratio, A.seen, A.hid, A.down, tostring(A.broken), tostring(A.rbroken), dec, tostring(e.o.n),
                e.phase == "parley" and ", after parley" or "", A.wtxt and (" worth: " .. A.wtxt) or ""))
        else
          dec = "attack"   -- не прочиталось после угрозы — как раньше: охота
          N.log(string.format("appraise: fallback %s after parley: %s - assault package as before", tostring(e.o.n), tostring(why)))
          N.appr_n = N.appr_n or {}; N.appr_n.fallback = (N.appr_n.fallback or 0) + 1
        end
        if dec ~= "parley" then N.appr[key] = nil end
        N.appr_act(C, S, e, A or { app = 0, own = 0 }, dec, cfg)
      elseif now - e.t0 > cfg.appr_max_s then
        N.appr[key] = nil
        N.appr_n = N.appr_n or {}; N.appr_n.fallback = (N.appr_n.fallback or 0) + 1
        N.log(string.format("appraise: fallback %s: %s - assault package as before", tostring(e.o.n),
              A and (A.near and "nobody seen" or "never came close") or tostring(why)))
      end
    end
  end
end
function N.regroup_day(M, O, day, force)   -- ушедший соперник снова на следе: пакет охоты (постоянный — через доску его платуна)
  local cfg = N.cfg()
  force = force or N.appr_off or cfg.appraise == false   -- оценки нет: пересматривать некому, охота возвращается сразу
  for _, o in ipairs(N.rivals(O)) do
    if o.pg.wd_day and (force or day - o.pg.wd_day >= cfg.appr_regroup_days) then
      if not o.pk then o.pg.wd_day = nil   -- временный отряд: новый спавн и так получит пакет охоты
      elseif M.find_pl then
        local p = M.find_pl(o)
        if p and N.appr_pkg(o, function() return p:getBlackboard() end, "hunt") then
          o.pg.wd_day = nil
          N.log("appraise: regroup " .. tostring(o.n) .. " - back on the trail")
        end
      end
    end
  end
end
function N.nearest_pc(ch)   -- ближайший к говорящему персонаж игрока (адресат ванильной реплики)
  local okp, p = pcall(function() return ch:getPosition() end)
  local best, bd
  pcall(function()
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      local q = okp and p and pc:getPosition()
      local d = q and ((q.x - p.x) ^ 2 + (q.z - p.z) ^ 2) or 0
      if not bd or d < bd then best, bd = pc, d end
    end
  end)
  return best
end
-- Ванильная реплика повода: Character:sendDialogEvent(target, EventTriggerEnum) (BindingsReference, ✓код); строку выбирает диалоговый
-- пакет NPC. Вернула не true (у пакета нет строки на повод, ?) или ошибка — false, говорим свою строку.
function N.vanilla_ev(ch, name)
  local cfg = N.cfg()
  if cfg.vanilla_lines == false or (N.ev_fail or 0) >= cfg.vanilla_fail_max then return false end
  local E = rawget(_G, "EventTriggerEnum")
  local what = (type(E) == "table" and E[name]) or N.EV[name]
  local tgt = what and N.nearest_pc(ch)
  if not tgt then return false end
  local ok, r = pcall(function() return ch:sendDialogEvent(tgt, what) end)
  if not ok then
    N.ev_fail = (N.ev_fail or 0) + 1
    N.log("vanilla_ev failed (" .. name .. "): " .. tostring(r) .. ((N.ev_fail >= cfg.vanilla_fail_max) and "; own lines only until restart" or ""))
    return false
  end
  if r ~= true then
    N.ev_quiet = N.ev_quiet or {}
    if not N.ev_quiet[name] then N.ev_quiet[name] = true; N.log("vanilla_ev: " .. name .. " not answered by dialogue package, own line") end
    return false
  end
  return true
end
function N.flush_said()
  local keep = {}
  for _, s in ipairs(N.said) do
    if os.clock() >= s.t then
      if s.ev and N.vanilla_ev(s.leader, s.ev) then
        N.log("said_ev: " .. s.ev .. " (vanilla line instead of: " .. s.line .. ")")
      else
        local oks = pcall(function() s.leader:say(s.line) end)
        if not oks then pcall(function() s.leader:sayALine(s.line, true) end) end   -- ENGINE_FINDINGS: sayALine(line, force) — запасной путь
        N.log((s.shop and "shop_talk: " or s.greet and "town_greet: " or s.amb and ("ambient_" .. s.amb .. ": ") or s.banter and "banter: " or s.talk and "town_talk: " or s.aid and "aid_said: " or "said: ") .. s.line)
      end
    elseif os.clock() < s.t + 60 then keep[#keep + 1] = s end
  end
  N.said = keep
end

-- должники ------------------------------------------------------------------------------------------------------------------
function N.is_player(ch) local ok, v = pcall(function() return ch:isPlayerCharacter() end); return ok and v == true end
function N.ident(ch)
  local okn, nm = pcall(function() return ch:getName() end)
  local okf, fid = pcall(function() local f = ch:getFaction(); local gd = f and (f:getData() or f.data); return gd and gd.stringID end)
  local okp, p = pcall(function() return ch:getPosition() end)
  if not (okn and nm and okf and fid) then return nil end
  return { n = nm, fid = fid, x = okp and p and p.x, z = okp and p and p.z }
end
function N.debt(ch, deed)
  local cfg = N.cfg()
  if not cfg.debts then return nil end
  local C = rawget(_G, "KMM_Conductor")
  local M, O, D = N.outlaws()
  if not (C and D) then return nil end
  local S = C.state()
  if not S then return nil end
  local id = N.ident(ch)
  if not id then return nil end
  local okpf, pf = pcall(function() return C.cfg().player_faction end)
  if okpf and pf and id.fid == pf then return nil end
  local X = N.state(S)
  X.debts = X.debts or {}
  local key = id.fid .. "|" .. id.n
  if X.debts[key] then return X.debts[key] end
  local nd = 0; for _ in pairs(X.debts) do nd = nd + 1 end
  if nd >= cfg.max_debts then return nil end
  local t, rg = N.where(D, id.x, id.z)
  local base = N.base_name(id.n)
  local dbt = { n = base, orig = id.n, fid = id.fid, deed = deed, place = (t and t.name) or rg or "the road", day = N.day(C), region = rg }
  X.debts[key] = dbt
  N.emit(C, nil, "debt_made", string.format(deed == "freed" and "The Nameless cut the chains of %s near %s." or "The Nameless saved the life of %s near %s.",
         base, dbt.place), { leader_name = base, a = id.fid, deed = deed, region = rg, x = id.x, z = id.z })
  return dbt
end
function N.on_first_aid(stats, patient, dt)
  if N.off then return end
  local okm, medic = pcall(function() return stats.me end)
  if not (okm and medic) or not N.is_player(medic) or N.is_player(patient) then return end
  local okn, nm = pcall(function() return patient:getName() end)
  if not okn then return end
  N.heal = N.heal or {}
  local h = N.heal[nm] or 0
  if h < 0 then return end   -- уже записан
  h = h + (tonumber(dt) or 0)
  if h >= N.cfg().heal_need then
    N.heal[nm] = -1
    N.debt(patient, "healed")
  else N.heal[nm] = h end
end
function N.on_lockpick(stats, lvl, ok)
  if N.off or not ok then return end
  local okm, me = pcall(function() return stats.me end)
  if okm and me and N.is_player(me) then N.lock_t = os.clock() end
end
function N.on_chained(ch, on)
  if N.off or N.is_player(ch) then return end
  local C = rawget(_G, "KMM_Conductor")
  local okc, sc = pcall(function() return C and C.self_chaining and C.self_chaining() end)
  if okc and sc then return end   -- заковал сам дирижёр (материализация слуха), не игрок и не мир рядом
  if on == true then
    if N.cfg().leaders ~= false then N.chained_leader(ch) end
    N.captive_in(ch)
  elseif on == false then
    local by_player = N.lock_t and os.clock() - N.lock_t <= N.cfg().lockpick_window
    local was = N.captive_out(ch)
    if by_player then N.debt(ch, "freed")
    elseif was then N.escaped(was) end
  end
end
function N.captive_key(ch)
  local id = N.ident(ch)
  return id and (id.fid .. "|" .. id.n), id
end
function N.captive_in(ch)   -- закован рядом с игроком: запомнить пленника (в сейве дирижёра)
  local cfg = N.cfg()
  if not cfg.captives then return end
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state()
  if not S then return end
  local key, id = N.captive_key(ch)
  local px, pz = N.player_pos()
  if not (key and px and id.x) or (px - id.x) ^ 2 + (pz - id.z) ^ 2 > cfg.captive_r ^ 2 then return end
  local okpf, pf = pcall(function() return C.cfg().player_faction end)
  if okpf and pf == id.fid then return end
  local X = N.state(S)
  X.captives = X.captives or {}
  if X.captives[key] then return end
  local n, oldest = 0, nil
  for k, v in pairs(X.captives) do n = n + 1; if not oldest or v.day < X.captives[oldest].day then oldest = k end end
  if n >= cfg.max_captives and oldest then X.captives[oldest] = nil end
  X.captives[key] = { n = id.n, fid = id.fid, x = id.x, z = id.z, day = N.day(C) }
  N.log("captive: " .. id.n .. " (" .. id.fid .. ")")
end
function N.captive_out(ch)
  local C = rawget(_G, "KMM_Conductor")
  local S = C and C.state()
  if not S then return nil end
  local X = N.state(S)
  local key = N.captive_key(ch)
  local v = key and X.captives and X.captives[key]
  if v then X.captives[key] = nil end
  return v
end
function N.rescue_step(C, S)   -- пленник в цепях дольше rescue_after_h: одна попытка его фракции на пленника
  local cfg = N.cfg()
  if not cfg.rescue then return end
  local X = N.state(S)
  if not X.captives then return end
  local day = N.day(C)
  for key, v in pairs(X.captives) do
    if not v.rt and (day - v.day) * 24 >= cfg.rescue_after_h then
      v.rt = day
      if math.random() < cfg.rescue_p and day - (X.rescue_day or -1000) >= cfg.rescue_cd_days then
        if N.rescue(C, S, v) then X.rescue_day = day; return end
      end
    end
  end
end
function N.rescue(C, S, v)
  local T = rawget(_G, "KMM_Traces")
  local M, O, D = N.outlaws()
  if not (T and T.request and M and D) then return false end
  local px, pz = N.player_pos()
  if not px then return false end
  local sid = M.tier_sid(D, v.fid, 1)
  if not sid then return false end
  local cfg = N.cfg()
  local a = math.random() * 6.2832
  local base = N.base_name(v.n)
  local job = { tag = "rescue", fid = v.fid, sid = sid, n = 1, size = 4, from_x = px + math.cos(a) * 2500, from_z = pz + math.sin(a) * 2500, to_x = px, to_z = pz,
                on_spawn = function(pls)
                  local pl = pls and pls[1]
                  local okl, leader = pcall(function() return pl:getSquadLeader() end)
                  if not (okl and leader) then return end
                  N.said[#N.said + 1] = { leader = leader, line = string.format(N.pick(N.SAY.rescue), base), t = os.clock() + cfg.say_delay_s,
                                          ev = "EV_KIDNAPPING_MY_ALLY" }   -- ванильный повод «уводят нашего»
                end }
  local okq, acc = pcall(T.request, job)
  if not (okq and acc) then return false end
  local okn, fname = pcall(C.name, v.fid)
  N.emit(C, nil, "nemesis_rescue", string.format("%s sent men to take back %s from the Nameless.", okn and fname or v.fid, base),
         { leader_name = base, a = v.fid })
  return true
end
function N.escaped(v)   -- вырвался не через взлом игрока: соперник с делом «escaped»
  local cfg = N.cfg()
  if math.random() >= cfg.escape_p then return end
  local C = rawget(_G, "KMM_Conductor")
  local M, O, D = N.outlaws()
  if not (C and M and O and D) then return end
  local S = C.state()
  local c = { n = v.n, fid = v.fid, x = v.x, z = v.z, lead = false, hits = 0 }
  N.make(M, O, D, C, S, c, "escaped")
end
function N.chained_leader(ch)   -- лидер города закован (игроком рядом или кем-то): модель мира узнаёт
  local C = rawget(_G, "KMM_Conductor")
  if not (C and C.leader_fell) then return end
  local oks, sid = pcall(function() local gd = ch:getGameData(); return gd and gd.stringID end)
  if not (oks and sid) then return end
  local px, pz = N.player_pos()
  local okp, p = pcall(function() return ch:getPosition() end)
  local near = px and okp and p and ((px - p.x) ^ 2 + (pz - p.z) ^ 2) < 1500 ^ 2
  local okl, lev = pcall(C.leader_fell, sid, nil, "captured", near and true or false)
  if okl and lev then N.log("leader_fell: " .. tostring(lev.text)); if near then N.banter("leader_fell"); N.deed_add(C, "leader_fell", lev.leader_name, p.x, p.z); pcall(function() N.count(C.state(), "leaders") end) end end
end
function N.on_player_attacked(attacker_fid)   -- зовёт дирижёр: на игрока напали — должник может прийти
  if N.off then return end
  local cfg = N.cfg()
  local C = rawget(_G, "KMM_Conductor")
  local T = rawget(_G, "KMM_Traces")
  local M, O, D = N.outlaws()
  if not (C and T and T.request and M) then return end
  local S = C.state()
  local X = N.state(S)
  local day = N.day(C)
  if not X.debts or day - (X.help_day or -1000) < cfg.help_cd_days then return end
  local pf = C.cfg().player_faction
  local px, pz = N.player_pos()
  if not px then return end
  for key, d in pairs(X.debts) do
    if not d.paid and day - d.day >= cfg.help_min_days and d.fid ~= attacker_fid and (C.rel(d.fid, pf) or 0) >= 0
       and (C.rel(d.fid, attacker_fid) or 0) <= 0 then
      local sid = M.tier_sid(D, d.fid, 1)
      if sid then
        local a = math.random() * 6.2832
        local job = { tag = "debt", fid = d.fid, sid = sid, n = 1, size = 3, from_x = px + math.cos(a) * 2500, from_z = pz + math.sin(a) * 2500,
                      to_x = px, to_z = pz,
                      on_spawn = function(pls)
                        local pl = pls and pls[1]
                        local okl, leader = pcall(function() return pl:getSquadLeader() end)
                        if not (okl and leader) then return end
                        pcall(function() leader:setName(d.n) end)
                        local line = string.format(N.pick(N.SAY[d.deed] or N.SAY.healed), d.place)
                        N.said[#N.said + 1] = { leader = leader, line = line, t = os.clock() + cfg.say_delay_s }
                        N.remember(leader, d.deed == "freed" and "LT_FREED_ME" or "LT_MY_LIFESAVER")
                      end }
        local okq, acc = pcall(T.request, job)
        if okq and acc then
          d.paid = day; X.help_day = day; X.repaid = (X.repaid or 0) + 1
          N.emit(C, nil, "debt_repaid", string.format("%s came running to help the Nameless: %s.", d.n,
                 d.deed == "freed" and "a debt for broken chains" or "a debt of blood"), { leader_name = d.n, a = d.fid, deed = d.deed })
          return true
        end
      end
    end
  end
end
function N.debts_day(C, S, day)   -- долг, не возвращённый боем, — доброй молвой
  local cfg = N.cfg()
  local X = N.state(S)
  local pf = C.cfg().player_faction
  for key, d in pairs(X.debts or {}) do
    if d.paid and day - d.paid > 60 then X.debts[key] = nil
    elseif not d.paid and day - d.day >= cfg.word_days then
      d.paid = day
      pcall(C.add_rel, d.fid, pf, cfg.word_rel)
      N.emit(C, nil, "debt_word", string.format("%s tells anyone who will listen that the Nameless %s near %s.", d.n,
             d.deed == "freed" and "broke his chains" or "saved his life", d.place), { leader_name = d.n, a = d.fid, deed = d.deed })
    end
  end
end
-- дела ядра (Q3) -------------------------------------------------------------------------------------------------------------
-- Шина KMM_Deeds: a — кто сделал, b — к кому (чьё отношение меняет ядро); by_player = a игрок, to_player = b игрок. Ядро уже само
-- поправило отношения (affectRelations), текст дела уже в хронике — здесь только последствия у людей: память, реплика, долг, город.
function N.helper(fid, x, z, cfg)   -- живой NPC фракции fid рядом с игроком (снимок KMM_Gov) или nil
  if not x then x, z = N.player_pos() end
  if not x then return nil end
  local G = rawget(_G, "KMM_Gov")
  local okS, snap = pcall(function() return G and G.snapshot and G.snapshot(5) end)
  if not (okS and snap and snap.list) then return nil end
  local best, bd = nil, cfg.aid_r ^ 2
  for _, r in ipairs(snap.list) do
    if r.fid == fid and not r.dead and r.x then
      local d2 = (r.x - x) ^ 2 + (r.z - z) ^ 2
      if d2 < bd then
        local okd, dn = pcall(function() return r.ch:isDead() or r.ch:isDown() end)
        if okd and not dn then best, bd = r.ch, d2 end
      end
    end
  end
  return best
end
function N.fname(C, fid) local ok, n = pcall(C.name, fid); return (ok and n and n ~= "") and n or tostring(fid) end
function N.deed_aid(C, S, ev, cfg)   -- фракция помогла игроку: долг перед игроком закрыт или игрок теперь должен
  local X = N.state(S)
  local day = N.day(C)
  local fid, fname = ev.a, N.fname(C, ev.a)
  X.owe = X.owe or {}
  local dd
  for _, d in pairs(X.debts or {}) do
    if d.fid == fid and not d.paid and day - d.day >= cfg.help_min_days and (not dd or d.day < dd.day) then dd = d end
  end
  local o = X.owe[fid]
  local fresh = dd or not (o and math.floor(o.last or -1) == math.floor(day))   -- реплика/память — раз на фракцию в день
  local helper = fresh and N.helper(fid, ev.x, ev.z, cfg)
  local hn
  if helper then pcall(function() hn = helper:getName() end) end
  local line
  if dd then   -- существующий долг перед игроком вернули делом, без отряда Traces
    dd.paid = day; X.repaid = (X.repaid or 0) + 1
    N.emit(C, nil, "debt_repaid", string.format("%s stood by the Nameless in a fight: %s.", fname,
           dd.deed == "freed" and "a debt for broken chains" or "a debt of blood"), { leader_name = dd.n, a = fid, deed = dd.deed, via = ev.kind })
    line = string.format(N.pick(N.SAY.aid_even), dd.n, dd.place)
  else
    if not o then
      local n, old = 0, nil
      for k, v in pairs(X.owe) do n = n + 1; if not old or v.day < X.owe[old].day then old = k end end
      if n >= cfg.max_debts and old then X.owe[old] = nil end
      o = { fid = fid, day = day, n = 0 }
      X.owe[fid] = o
    end
    o.n = o.n + 1; o.day = day; o.kind = ev.kind; o.place = ev.town_name or o.place; o.who = hn or o.who
    N.log(string.format("deed_owed: %s (%s) %s for the Nameless, helper %s", fname, fid, tostring(ev.kind), tostring(hn or "not loaded")))
    if fresh then
      o.last = day
      line = N.pick(N.SAY.aid_owe)
      N.deed_add(C, "deed_owed", fname, ev.x, ev.z, { fid = fid })
    end
  end
  if helper then
    N.remember(helper, "LT_FRIENDLY_AQUAINTANCE")   -- родная память ядра: этот отряд игроку знаком по общему бою
    if line then N.said[#N.said + 1] = { leader = helper, line = line, t = os.clock() + 2, aid = true } end
  end
end
function N.deed_by_player(C, S, ev, cfg)   -- игрок сделал фракции b: неблагодарность / долг вернул / город помнит
  local X = N.state(S)
  local day = N.day(C)
  local fid, fname = ev.b, N.fname(C, ev.b)
  if ev.witnessed == false then   -- Y1: дела без свидетелей город не помнит, неблагодарности не видно (nil/true — как раньше)
    N.log(string.format("deed_unseen: %s against %s - no witnesses, town does not remember", tostring(ev.kind), fname))
    return
  end
  local o = X.owe and X.owe[fid]
  local ingrate = false
  if o and ev.tone == "harm" then
    X.owe[fid] = nil; ingrate = true
    N.log(string.format("deed_ingrate: the Nameless %s %s, who had helped them", tostring(ev.kind), fname))
  elseif o and ev.tone == "help" then
    X.owe[fid] = nil
    N.log(string.format("deed_owed_repaid: the Nameless repaid %s (%s)", fname, tostring(ev.kind)))
  end
  local g = N.DEED_G[ev.kind]
  local owner
  if ev.town_sid and C.town_mood then
    local okm, mood = pcall(C.town_mood, ev.town_sid)
    owner = okm and type(mood) == "table" and mood.owner or nil
  end
  if ingrate then
    N.deed_add(C, "deed_ingrate", fname, ev.x, ev.z, { fid = fid, tsid = owner == fid and ev.town_sid or nil, gk = "ingrate" })
    return
  end
  if not (g and owner and owner == fid and ev.x) then return end   -- город помнит только дела против/за своего хозяина
  for _, d in ipairs(X.deeds or {}) do   -- лидер города уже лёг от игрока — это дело и так помнят (leader_fell)
    if d.k == "leader_fell" and day - d.day < 1 and (d.x - ev.x) ^ 2 + (d.z - ev.z) ^ 2 < cfg.talk_r ^ 2 then return end
  end
  if N.deed_add(C, "deed_" .. g, fname, ev.x, ev.z, { fid = fid, tsid = ev.town_sid, gk = g }) then
    N.log(string.format("deed_town: %s %s at %s", g, fid, tostring(ev.town_name or ev.town_sid)))
  end
end
function N.on_deed(ev)
  if N.off or N.deeds_off or type(ev) ~= "table" then return end
  local cfg = N.cfg()
  if not cfg.deeds then return end
  local ok, err = pcall(function()
    local C = rawget(_G, "KMM_Conductor")
    local S = C and C.state and C.state()
    if type(S) ~= "table" then return end
    if ev.to_player and ev.tone == "help" and ev.a then N.deed_aid(C, S, ev, cfg)
    elseif ev.by_player and ev.b then N.deed_by_player(C, S, ev, cfg) end
  end)
  if not ok then N.deeds_off = true; N.log("deeds disabled until restart: " .. tostring(err)) end
end
function N.sub_deeds()   -- подписка на шину дирижёра (из тика, один раз)
  local C = rawget(_G, "KMM_Conductor")
  if not (C and C.subscribe) then return end
  N.deeds_sub = true
  local ok, id = pcall(C.subscribe, "deed", function(ev) N.on_deed(ev) end)
  N.log(ok and "deeds: subscribed to deed bus" or ("deeds: subscribe failed: " .. tostring(id)))
end
function N.owe_day(S, day)   -- долг игрока перед фракцией забывается
  local X = N.state(S)
  for fid, o in pairs(X.owe or {}) do if day - (o.day or 0) > N.cfg().owe_days then X.owe[fid] = nil end end
end
-- P4 (B2): родная долгая память ядра. Числа — CharacterPerceptionTags_LongTerm из Character.h:87-101 (✓код), не из Lua-энума.
-- Пишем только через плагин (KMM_Native.remember_lt -> Character::rememberCharacter(LT), RVA 0x6732A0): Lua-метод
-- rememberCharacter имеет две перегрузки (ST/LT) с числовыми энумами и может записать ShortTerm-тег. Нет плагина — не пишем.
N.LT = { LT_MY_INTRUDER = 1, LT_MY_LIFESAVER = 2, LT_FREED_ME = 3, LT_STOLE_FROM_ME = 4, LT_MY_CAPTOR = 5,
         LT_FRIENDLY_AQUAINTANCE = 6, LT_DEFEATED_MY_SQUAD_ONCE = 7, LT_SQUAD_LOST_TO_ME_ONCE = 8,
         LT_KILLED_MY_FRIEND = 9, LT_I_SCREWED_THIS_GUY = 10 }
N.REMEMBER_MAX = 16   -- помнит весь отряд игрока (диалог проверяет того, кто говорит), но не больше стольких персонажей
function N.remember(leader, tagname)
  if leader == nil or N.cfg().native_memory == false then return end
  local tag = N.LT[tagname]
  if not tag then N.log("remember: unknown tag " .. tostring(tagname)); return end
  local KN = rawget(_G, "KMM_Native")
  local okh, has = pcall(function() return KN and KN.has_memory and KN.has_memory() end)
  if not (okh and has == true) then
    if not N.mem_nonative then N.mem_nonative = true; N.log("remember: no native (KMM_Native.remember_lt missing), core memory not written") end
    return
  end
  local okw, err = pcall(function()
    local n, bad, why = 0, 0, nil
    for _, pc in pairs(getPlayerInterface():getAllPlayerCharacters()) do
      if n + bad >= N.REMEMBER_MAX then break end
      local r, w = KN.remember_lt(leader, pc, tag)
      if r == true then n = n + 1 else bad = bad + 1; why = why or w end
    end
    local nm = "?"
    pcall(function() nm = tostring(leader:getName()) end)
    if n > 0 then N.log(string.format("remember: %s=%d written for %d player chars by %s", tagname, tag, n, nm))
    else N.log(string.format("remember: %s failed for %s: %s", tagname, nm, tostring(why or "no player chars"))) end
  end)
  if not okw then N.log("remember: error " .. tostring(err)) end
end
function N.hooks()   -- новые колбэки ядра (не _NV_): регистрируются из первого тика, каждый под guarded
  if N.hooked or not (Events and Events.on) or N.cfg().debts == false then return end
  N.hooked = true
  N.hook_off = N.hook_off or {}
  local function guarded(name, fn)   -- сбой нового колбэка выключает только его (немезис, охотники, лидеры по ударам живут дальше)
    return function(...)
      if N.off or N.hook_off[name] then return end
      local ok, err = pcall(fn, ...)
      if not ok then N.hook_off[name] = true; N.log("hook " .. name .. " disabled until restart: " .. tostring(err)) end
    end
  end
  pcall(function() Events.on("CharStats::xpFirstAid", guarded("first_aid", function(st, pt, dt) N.on_first_aid(st, pt, dt) end)) end)
  pcall(function() Events.on("CharStats::xpLockpicking", guarded("lockpick", function(st, lvl, ok) N.on_lockpick(st, lvl, ok) end)) end)
  pcall(function() Events.on("Character::setChainedMode", guarded("chained", function(ch, on) N.on_chained(ch, on) end)) end)
  pcall(function() Events.on("ForgottenGUI::showTradeWindow", guarded("trade", function(gui, a, b) N.on_trade(a, b) end)) end)
  N.log("debt hooks registered")
end

-- тик ------------------------------------------------------------------------------------------------------------------------
function N.tick()
  if N.off then return end
  local cfg = N.cfg()
  if cfg.enabled == false or os.clock() - N.last < cfg.tick_s then return end
  N.last = os.clock()
  if not N.hooked then N.hooks() end
  if not N.deeds_sub then N.sub_deeds() end
  if #N.said > 0 then N.flush_said() end
  local M, O, D, C, S = N.outlaws()
  if not M then return end
  if not N.beat_off and cfg.rival_p_beat ~= false then
    local okb, eb = pcall(N.beat_scan, C, S)
    if not okb then N.beat_off = true; N.log("beat memory disabled until restart: " .. tostring(eb)) end
  end
  if next(N.cand) then N.resolve(M, O, D, C, S) end
  if N.appr and next(N.appr) and not N.appr_off then
    local oka, ea = pcall(N.appraise_step, C, S)
    if not oka then N.appr_stop(C, "appraise disabled until restart: " .. tostring(ea)) end
  end
  if N.regroup_now and not N.regroup_off then N.regroup_now = nil; N.regroup_safe(M, O, math.floor(N.day(C))) end
  if not N.scars_off then
    local oks, es = pcall(N.scars, C, S, D)
    if not oks then N.scars_off = true; N.log("scars disabled until restart: " .. tostring(es)) end
  end
  if not N.rescue_off then
    local okr, er = pcall(N.rescue_step, C, S)
    if not okr then N.rescue_off = true; N.log("rescue disabled until restart: " .. tostring(er)) end
  end
  if not N.talk_off then
    local okt, et = pcall(N.town_talk, C, S)
    if not okt then N.talk_off = true; N.log("town_talk disabled until restart: " .. tostring(et)) end
  end
  if not N.chron_off then
    local okh, eh = pcall(N.chronicle, C, S)
    if not okh then N.chron_off = true; N.log("chronicle disabled until restart: " .. tostring(eh)) end
  end
  if not N.greet_off then
    local okg, eg = pcall(N.greet, C, S)
    if not okg then N.greet_off = true; N.log("greet disabled until restart: " .. tostring(eg)) end
  end
  if not N.amb_off then
    local oka, ea = pcall(N.ambient, C, S)
    if not oka then N.amb_off = true; N.log("ambient disabled until restart: " .. tostring(ea)) end
  end
  local X = N.state(S)
  local day = math.floor(N.day(C))
  if day <= 0 then return end
  if not X.day then X.day = day end
  if day > X.day then
    for d = X.day + 1, math.min(day, X.day + 3) do
      N.day_step(M, O, D, C, S, d); N.debts_day(C, S, d); N.owe_day(S, d)
      if not N.regroup_off then N.regroup_safe(M, O, d) end   -- и при выключенной оценке: пакет «бродить» не остаётся навсегда
      if not N.co_off then
        local okc, ec = pcall(N.co_day, M, O, D, C, S, d)
        if not okc then N.co_off = true; N.log("company disabled until restart: " .. tostring(ec)) end
      end
    end
    X.day = day
  end
end
function N.regroup_safe(M, O, d, force)   -- регрупп под своим флагом: ошибка выключает только его
  local ok, e = pcall(N.regroup_day, M, O, d, force)
  if not ok then N.regroup_off = true; N.log("regroup disabled until restart: " .. tostring(e)) end
end
function N.guarded()
  local ok, err = pcall(function()
    local G = rawget(_G, "KMM_Gov")
    if G and G.run then return G.run("nemesis", N.tick) end
    return N.tick()
  end)
  if not ok then N.fail("tick", err) end
end

KMM_Nemesis = {
  on_player_hit = function(v, a) return N.on_player_hit(v, a) end,
  on_spawn = function(o, leader) return N.on_spawn(o, leader) end,
  on_dead = function(o, how) return N.on_dead(o, how) end,
  on_player_attacked = function(fid) return N.on_player_attacked(fid) end,
  on_hunt = function(pl, hfid, client, amount) return N.on_hunt(pl, hfid, client, amount) end,
  hunt_bonus = function(hfid) return N.hunt_bonus(hfid) end,
  hunters = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state(); return S and N.hunters(S) or {} end,
  on_first_aid = function(st, pt, dt) return N.on_first_aid(st, pt, dt) end,
  on_lockpick = function(st, lvl, ok) return N.on_lockpick(st, lvl, ok) end,
  on_chained = function(ch, on) return N.on_chained(ch, on) end,
  banter = function(typ, deed) return N.banter(typ, deed) end,
  hook_off = function() return N.hook_off or {} end,
  deeds = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state(); return S and N.state(S).deeds or {} end,
  town_talk_off = function() return N.talk_off end,
  ambient_off = function() return N.amb_off end,
  trait_of = function(nm) return N.trait_of(nm) end,
  greet_off = function() return N.greet_off end,
  -- событие хроники дирижёра (ev.id) уже записано хроникой Nemesis во вкладку сообщений (addMessage ok): true; второе значение — стоит в очереди
  chronicled = function(id)
    if id == nil then return false, false end
    local sent = N.chron_sent ~= nil and N.chron_sent[id] == true
    local q = false
    for _, x in ipairs(N.chron_qi or {}) do if x == id then q = true end end
    return sent, q
  end,
  -- greet за ТЕКУЩИЙ визит в город tsid: said = житель уже сказал (реплика в очереди/сказана); pending = игрок в этом городе и greet ещё может
  -- сказать (ждёт greet_delay_s или жителя рядом). Визит кончается, когда игрок вышел из города. Для KMM_Rumors: не говорить вторым подряд.
  greet_said = function(tsid)   -- Nemesis выключен (ошибка/greet_off) — greet не скажет: false, false (иначе «ждём» навсегда глушит мелочь Rumors)
    if N.off or N.greet_off then return false, false end
    return N.greet_visit ~= nil and N.greet_visit == tsid, (N.greet_town == tsid and N.greet_at ~= nil and N.greet_visit == nil) end,
  chronicle_off = function() return N.chron_off end,
  on_trade = function(a, b) return N.on_trade(a, b) end,
  player_title = function() local C = rawget(_G, "KMM_Conductor"); return C and N.title(C) end,
  counts = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state(); return S and N.state(S).cnt or {} end,
  company = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state(); return S and N.state(S).co end,
  captives = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state(); return S and N.state(S).captives or {} end,
  debts = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state(); return S and N.state(S).debts or {} end,
  owe = function() local C = rawget(_G, "KMM_Conductor"); local S = C and C.state(); return S and N.state(S).owe or {} end,
  on_deed = function(ev) return N.on_deed(ev) end,
  deeds_off = function() return N.deeds_off end,
  rivals = function() local M, O = N.outlaws(); return O and N.rivals(O) or {} end,
  remember = function(leader, tagname) return N.remember(leader, tagname) end,
  disabled = function() return N.off and { nemesis = true } or {} end,
  appraisals = function() return N.appr_n or {} end,
  worth = function() local ok, W = pcall(N.worth, rawget(_G, "KMM_Conductor")); return ok and W or nil end,   -- богатство/слава игрока (ванильные числа)
  poor = function() return N.poor(rawget(_G, "KMM_Conductor")) end,   -- взять нечего и бояться некого (contempt, ворота Traces, запах Predators)
  appraise_off = function() return N.appr_off end,
  withdrew_recent = function(x, days) local ok, r = pcall(N.withdrew_recent, x, days); return ok and r == true end,
  _tick = function() N.last = -1000; N.tick() end,
  _N = N,
}
if Events and Events.on then pcall(Events.on, "GameWorld::charsUpdate", N.guarded) end

-- PUBLISH (2026-11-16): KenshiLua runs each init script in its own sandbox; a plain global stays inside it.
if KMM_Nemesis ~= nil then rawset(_G, "KMM_Nemesis", KMM_Nemesis) end
