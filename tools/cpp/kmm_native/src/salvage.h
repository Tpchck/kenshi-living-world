// KMM_Native 2.4: context-menu "Salvage Parts" (downed skeletons) / "Butcher" (downed animals).
// Shared between kmm_native.cpp (minimal declarations, owns the log) and salvage.cpp (full KenshiLib + MyGUI headers).
// Only plain C types cross this boundary, so the two translation units never see each other's class declarations.
#pragma once

// defined in kmm_native.cpp: "KMM_Native: <msg>" into RE_Kenshi_log.txt (ErrorLog when isError)
void KmmLog(bool isError, const char* fmt, ...);

// defined in salvage.cpp. Parses the rules file now (game data is resolved lazily on the first menu),
// installs the ContextMenu::showContextMenu and GameWorld::_NV_mainLoop_GPUSensitiveStuff hooks.
// Never throws; on any failure the menu items stay off and the reason is logged.
void Salvage_Install(const char* rulesPath, const char* offPath);
