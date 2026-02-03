const fs = require('fs');
const path = require('path');

// Lade flows.json
const flowsPath = path.join(__dirname, 'flows.json');
const flows = JSON.parse(fs.readFileSync(flowsPath, 'utf8'));

// Finde func_controller
flows.forEach(node => {
    if (node.id === 'func_controller') {
        const oldFunc = node.func;
        // Füge Reifen-Befehle ein
        const newFunc = oldFunc.replace(
            "// Tick - nur senden wenn aktiv",
            `// Reifen setzen
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

// Tick - nur senden wenn aktiv`
        );
        node.func = newFunc;
        console.log('✓ func_controller erweitert');
    }
});

// Finde func_generator
flows.forEach(node => {
    if (node.id === 'func_generator') {
        let newFunc = node.func;
        // Füge Reifen-Konstante hinzu
        newFunc = newFunc.replace(
            "const manualBattery = flow.get('manual_battery');",
            `const manualBattery = flow.get('manual_battery');
const manualTires = flow.get('manual_tires');`
        );
        // Füge Reifen-Initialisierung hinzu
        newFunc = newFunc.replace(
            "    tripStartFuel: null\n};",
            `    tripStartFuel: null,
    tires: 'winter'
};`
        );
        // Füge Reifen-Setzung hinzu
        newFunc = newFunc.replace(
            `if (manualBattery !== undefined && manualBattery !== null) {
    v.battery = manualBattery;
    flow.set('manual_battery', null);
}`,
            `if (manualBattery !== undefined && manualBattery !== null) {
    v.battery = manualBattery;
    flow.set('manual_battery', null);
}
if (manualTires !== undefined && manualTires !== null) {
    v.tires = manualTires;
    flow.set('manual_tires', null);
}`
        );
        node.func = newFunc;
        console.log('✓ func_generator erweitert');
    }
});

// Speichere flows.json
fs.writeFileSync(flowsPath, JSON.stringify(flows, null, 4), 'utf8');
console.log('✓ flows.json aktualisiert');
