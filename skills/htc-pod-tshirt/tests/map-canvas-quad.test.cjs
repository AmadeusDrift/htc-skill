const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const reference = fs.readFileSync(path.join(__dirname, '..', 'references', 'psd-mockup.md'), 'utf8');
const source = reference.match(/\x60\x60\x60javascript\n([\s\S]*?)\n\x60\x60\x60/)[1];
function runCase(quad) {
  const layer = {id: 17};
  Object.defineProperty(layer, 'bounds', {get() {throw new Error('Ink bounds must not be read');}});
  const original = {id: 99};
  const document = {activeLayer: original};
  const transform = [423, 574, 663, 574, 663, 874, 423, 874];
  let action = null;
  class Ref {
    putIdentifier(type, id) {this.id = id;}
    putEnumerated(...args) {this.enum = args;}
  }
  class List {
    constructor() {this.values = [];}
    putDouble(value) {this.values.push(value);}
  }
  class Descriptor {
    constructor() {this.values = {};}
    putReference(key, value) {this.values[key] = value;}
    putList(key, value) {this.values[key] = value.values;}
  }
  const context = {app: {activeDocument: document}, ActionReference: Ref,
    ActionList: List, ActionDescriptor: Descriptor,
    charIDToTypeID: value => value, stringIDToTypeID: value => value,
    DialogModes: {NO: 0},
    executeActionGet(ref) {
      assert.equal(ref.id, layer.id);
      return {getObjectValue() {return {getList() {return {getDouble(i) {return transform[i];}};}};}};
    },
    executeAction(name, payload) {
      assert.equal(name, 'Trnf');
      assert.equal(document.activeLayer.id, layer.id, 'Transform must target the read layer');
      action = payload.values;
    }};
  vm.createContext(context);
  vm.runInContext(source, context);
  let error;
  try {context.mapCanvasQuad(layer, quad);} catch (failure) {error = failure;}
  return {action, error, document, original, layer};
}
test('Transparent artwork maps the complete source canvas, not visible ink bounds', () => {
  const corners = [100, 200, 500, 220, 470, 720, 80, 690];
  const result = runCase(corners);
  assert.equal(result.error, undefined);
  assert.deepEqual(Array.from(result.action.rectangle), [423, 574, 663, 874]);
  assert.deepEqual(Array.from(result.action.quadrilateral), corners);
});
test('Explicitly selects target layer when another layer was previously active', () => {
  const result = runCase([0, 0, 100, 0, 100, 125, 0, 125]);
  assert.equal(result.error, undefined);
  assert.equal(result.document.activeLayer, result.layer);
});
test('Malformed corners fail before changing active layer or issuing a transform', () => {
  for (const corners of [null, [0, 1], [0, 0, 100, 0, 100, Infinity, 0, 125]]) {
    const result = runCase(corners);
    assert.ok(result.error);
    assert.equal(result.action, null);
    assert.equal(result.document.activeLayer, result.original);
  }
});
