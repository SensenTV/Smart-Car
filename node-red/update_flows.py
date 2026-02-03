#!/usr/bin/env python3
import json

# Lade flows.json
with open('flows.json', 'r', encoding='utf-8') as f:
    flows = json.load(f)

# Finde func_controller und erweitere um Reifen-Befehle
for node in flows:
    if node.get('id') == 'func_controller':
        old_func = node['func']
        # Füge Reifen-Befehle vor "// Tick - nur senden wenn aktiv" ein
        new_code = old_func.replace(
            "// Tick - nur senden wenn aktiv",
            """// Reifen setzen
if (cmd === 'set_tires:summer') {
    flow.set('manual_tires', 'summer');
    node.status({fill:'#FFC107', shape:'dot', text: 'Reifen: Sommer'});
    return msg;
}
if (cmd === 'set_tires:winter') {
    flow.set('manual_tires', 'winter');
    node.status({fill:'#2196F3', shape:'dot', text: 'Reifen: Winter'});
    return msg;
}

// Tick - nur senden wenn aktiv"""
        )
        node['func'] = new_code
        print("✓ func_controller erweitert")
        break

# Finde func_generator und erweitere um Reifen-Handling
for node in flows:
    if node.get('id') == 'func_generator':
        old_func = node['func']
        # Füge Reifen-Handling nach der Battery-Logik ein
        new_code = old_func.replace(
            "// Manuelle Werte uebernehmen falls gesetzt\nconst manualState = flow.get('manual_state');\nconst manualFuel = flow.get('manual_fuel');\nconst manualBattery = flow.get('manual_battery');",
            """// Manuelle Werte uebernehmen falls gesetzt
const manualState = flow.get('manual_state');
const manualFuel = flow.get('manual_fuel');
const manualBattery = flow.get('manual_battery');
const manualTires = flow.get('manual_tires');"""
        )
        # Füge Reifen-Setzung nach Battery-Setzung ein
        new_code = new_code.replace(
            """if (manualBattery !== undefined && manualBattery !== null) {
    v.battery = manualBattery;
    flow.set('manual_battery', null);
}""",
            """if (manualBattery !== undefined && manualBattery !== null) {
    v.battery = manualBattery;
    flow.set('manual_battery', null);
}
if (manualTires !== undefined && manualTires !== null) {
    v.tires = manualTires;
    flow.set('manual_tires', null);
}"""
        )
        # Speichere Reifen im Fahrzeugobjekt
        new_code = new_code.replace(
            "    tripCounter: context.get('tripCounter') || 0,\n    tripStartTime: null,\n    tripStartFuel: null",
            """    tripCounter: context.get('tripCounter') || 0,
    tripStartTime: null,
    tripStartFuel: null,
    tires: 'winter'"""
        )
        node['func'] = new_code
        print("✓ func_generator erweitert")
        break

# Speichere die Datei
with open('flows.json', 'w', encoding='utf-8') as f:
    json.dump(flows, f, indent=4, ensure_ascii=False)

print("✓ flows.json aktualisiert")
