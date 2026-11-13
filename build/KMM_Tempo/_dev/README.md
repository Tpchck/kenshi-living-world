# KMM_Tempo

Усталость от бега (игрок) и шаг/трусца отрядов NPC. Один скрипт: `scripts/init/kmm_tempo.lua`, конфиг в начале файла (`CFG`).

Поля API (BindingsReference): пишутся `CharStats.moveSpeed` (RW), `Platoon.speedOverride` (RW, MoveSpeed), `MedicalSystem.hunger` (RW, по умолчанию выключено). Читаются `Character:getMovementSpeed/getMovementSpeedOrders`, `Inventory:getTotalWeight`, `MedicalSystem:getMovementSpeedInjuryMultiplier`.
`travelSpeedLoaded/Unloaded` относятся к CampaignInstance, не к Platoon, — не используются.

## Темп x1–x5
- Усталость интегрируется по игровым часам (`getTotalDays()*24`, шаг ограничен 2 ч, в паузе dt = 0): на любой скорости игры один и тот же путь даёт ту же усталость.
- Реальное время (`os.clock`) задаёт только частоту опросов (игрок 1 с, NPC 2 с, ≤ 16 отрядов за такт) и стартовую задержку; на эффекты не влияет.
- Режим NPC — состояние (город: шаг, дорога: трусца, бой: ваниль), а не накопление, поэтому от скорости игры не зависит.

## Самоотключение
Каждая функция (`player_fatigue`, `player_slow`, `player_hunger`, `npc_pace`) отключается при первой ошибке или если записанное значение не читается обратно; причина — `logs/tempo.log` и `debug.log`.

Тест: `python -I -X utf8 build/KMM_Tempo/_dev/test_tempo.py`. Сборка: `python -I -X utf8 tools/build/kmm_build.py --write tempo`.
