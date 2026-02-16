// Compiles a dart2wasm-generated main module from `source` which can then
// instantiatable via the `instantiate` method.
//
// `source` needs to be a `Response` object (or promise thereof) e.g. created
// via the `fetch()` JS API.
export async function compileStreaming(source) {
  const builtins = {builtins: ['js-string']};
  return new CompiledApp(
      await WebAssembly.compileStreaming(source, builtins), builtins);
}

// Compiles a dart2wasm-generated wasm modules from `bytes` which is then
// instantiatable via the `instantiate` method.
export async function compile(bytes) {
  const builtins = {builtins: ['js-string']};
  return new CompiledApp(await WebAssembly.compile(bytes, builtins), builtins);
}

// DEPRECATED: Please use `compile` or `compileStreaming` to get a compiled app,
// use `instantiate` method to get an instantiated app and then call
// `invokeMain` to invoke the main function.
export async function instantiate(modulePromise, importObjectPromise) {
  var moduleOrCompiledApp = await modulePromise;
  if (!(moduleOrCompiledApp instanceof CompiledApp)) {
    moduleOrCompiledApp = new CompiledApp(moduleOrCompiledApp);
  }
  const instantiatedApp = await moduleOrCompiledApp.instantiate(await importObjectPromise);
  return instantiatedApp.instantiatedModule;
}

// DEPRECATED: Please use `compile` or `compileStreaming` to get a compiled app,
// use `instantiate` method to get an instantiated app and then call
// `invokeMain` to invoke the main function.
export const invoke = (moduleInstance, ...args) => {
  moduleInstance.exports.$invokeMain(args);
}

class CompiledApp {
  constructor(module, builtins) {
    this.module = module;
    this.builtins = builtins;
  }

  // The second argument is an options object containing:
  // `loadDeferredWasm` is a JS function that takes a module name matching a
  //   wasm file produced by the dart2wasm compiler and returns the bytes to
  //   load the module. These bytes can be in either a format supported by
  //   `WebAssembly.compile` or `WebAssembly.compileStreaming`.
  // `loadDynamicModule` is a JS function that takes two string names matching,
  //   in order, a wasm file produced by the dart2wasm compiler during dynamic
  //   module compilation and a corresponding js file produced by the same
  //   compilation. It should return a JS Array containing 2 elements. The first
  //   should be the bytes for the wasm module in a format supported by
  //   `WebAssembly.compile` or `WebAssembly.compileStreaming`. The second
  //   should be the result of using the JS 'import' API on the js file path.
  async instantiate(additionalImports, {loadDeferredWasm, loadDynamicModule} = {}) {
    let dartInstance;

    // Prints to the console
    function printToConsole(value) {
      if (typeof dartPrint == "function") {
        dartPrint(value);
        return;
      }
      if (typeof console == "object" && typeof console.log != "undefined") {
        console.log(value);
        return;
      }
      if (typeof print == "function") {
        print(value);
        return;
      }

      throw "Unable to print message: " + value;
    }

    // A special symbol attached to functions that wrap Dart functions.
    const jsWrappedDartFunctionSymbol = Symbol("JSWrappedDartFunction");

    function finalizeWrapper(dartFunction, wrapped) {
      wrapped.dartFunction = dartFunction;
      wrapped[jsWrappedDartFunctionSymbol] = true;
      return wrapped;
    }

    // Imports
    const dart2wasm = {
            _3: (o, t) => typeof o === t,
      _4: (o, c) => o instanceof c,
      _5: o => Object.keys(o),
      _7: (o,s,v) => o[s] = v,
      _8: (o, a) => o + a,
      _35: () => new Array(),
      _36: x0 => new Array(x0),
      _38: x0 => x0.length,
      _40: (x0,x1) => x0[x1],
      _41: (x0,x1,x2) => { x0[x1] = x2 },
      _42: (x0,x1) => x0.push(x1),
      _43: x0 => new Promise(x0),
      _45: (x0,x1,x2) => new DataView(x0,x1,x2),
      _47: x0 => new Int8Array(x0),
      _48: (x0,x1,x2) => new Uint8Array(x0,x1,x2),
      _49: x0 => new Uint8Array(x0),
      _51: x0 => new Uint8ClampedArray(x0),
      _53: x0 => new Int16Array(x0),
      _55: x0 => new Uint16Array(x0),
      _57: x0 => new Int32Array(x0),
      _59: x0 => new Uint32Array(x0),
      _61: x0 => new Float32Array(x0),
      _63: x0 => new Float64Array(x0),
      _65: (x0,x1,x2) => x0.call(x1,x2),
      _69: () => Symbol("jsBoxedDartObjectProperty"),
      _70: (decoder, codeUnits) => decoder.decode(codeUnits),
      _71: () => new TextDecoder("utf-8", {fatal: true}),
      _72: () => new TextDecoder("utf-8", {fatal: false}),
      _73: (s) => +s,
      _74: x0 => new Uint8Array(x0),
      _75: (x0,x1,x2) => x0.set(x1,x2),
      _76: (x0,x1) => x0.transferFromImageBitmap(x1),
      _77: x0 => x0.arrayBuffer(),
      _78: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._78(f,arguments.length,x0) }),
      _79: x0 => new window.FinalizationRegistry(x0),
      _80: (x0,x1,x2,x3) => x0.register(x1,x2,x3),
      _81: (x0,x1) => x0.unregister(x1),
      _82: (x0,x1,x2) => x0.slice(x1,x2),
      _83: (x0,x1) => x0.decode(x1),
      _84: (x0,x1) => x0.segment(x1),
      _85: () => new TextDecoder(),
      _87: x0 => x0.buffer,
      _88: x0 => x0.wasmMemory,
      _89: () => globalThis.window._flutter_skwasmInstance,
      _90: x0 => x0.rasterStartMilliseconds,
      _91: x0 => x0.rasterEndMilliseconds,
      _92: x0 => x0.imageBitmaps,
      _196: x0 => x0.stopPropagation(),
      _197: x0 => x0.preventDefault(),
      _199: x0 => x0.remove(),
      _200: (x0,x1) => x0.append(x1),
      _201: (x0,x1,x2,x3) => x0.addEventListener(x1,x2,x3),
      _246: x0 => x0.unlock(),
      _247: x0 => x0.getReader(),
      _248: (x0,x1,x2) => x0.addEventListener(x1,x2),
      _249: (x0,x1,x2) => x0.removeEventListener(x1,x2),
      _250: (x0,x1) => x0.item(x1),
      _251: x0 => x0.next(),
      _252: x0 => x0.now(),
      _253: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._253(f,arguments.length,x0) }),
      _254: (x0,x1) => x0.addListener(x1),
      _255: (x0,x1) => x0.removeListener(x1),
      _256: (x0,x1) => x0.matchMedia(x1),
      _257: (x0,x1) => x0.revokeObjectURL(x1),
      _258: x0 => x0.close(),
      _259: (x0,x1,x2,x3,x4) => ({type: x0,data: x1,premultiplyAlpha: x2,colorSpaceConversion: x3,preferAnimation: x4}),
      _260: x0 => new window.ImageDecoder(x0),
      _261: x0 => ({frameIndex: x0}),
      _262: (x0,x1) => x0.decode(x1),
      _263: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._263(f,arguments.length,x0) }),
      _264: (x0,x1) => x0.getModifierState(x1),
      _265: (x0,x1) => x0.removeProperty(x1),
      _266: (x0,x1) => x0.prepend(x1),
      _267: x0 => new Intl.Locale(x0),
      _268: x0 => x0.disconnect(),
      _269: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._269(f,arguments.length,x0) }),
      _270: (x0,x1) => x0.getAttribute(x1),
      _271: (x0,x1) => x0.contains(x1),
      _272: (x0,x1) => x0.querySelector(x1),
      _273: x0 => x0.blur(),
      _274: x0 => x0.hasFocus(),
      _275: (x0,x1,x2) => x0.insertBefore(x1,x2),
      _276: (x0,x1) => x0.hasAttribute(x1),
      _277: (x0,x1) => x0.getModifierState(x1),
      _278: (x0,x1) => x0.createTextNode(x1),
      _279: (x0,x1) => x0.appendChild(x1),
      _280: (x0,x1) => x0.removeAttribute(x1),
      _281: x0 => x0.getBoundingClientRect(),
      _282: (x0,x1) => x0.observe(x1),
      _283: x0 => x0.disconnect(),
      _284: (x0,x1) => x0.closest(x1),
      _707: () => globalThis.window.flutterConfiguration,
      _709: x0 => x0.assetBase,
      _714: x0 => x0.canvasKitMaximumSurfaces,
      _715: x0 => x0.debugShowSemanticsNodes,
      _716: x0 => x0.hostElement,
      _717: x0 => x0.multiViewEnabled,
      _718: x0 => x0.nonce,
      _720: x0 => x0.fontFallbackBaseUrl,
      _730: x0 => x0.console,
      _731: x0 => x0.devicePixelRatio,
      _732: x0 => x0.document,
      _733: x0 => x0.history,
      _734: x0 => x0.innerHeight,
      _735: x0 => x0.innerWidth,
      _736: x0 => x0.location,
      _737: x0 => x0.navigator,
      _738: x0 => x0.visualViewport,
      _739: x0 => x0.performance,
      _741: x0 => x0.URL,
      _743: (x0,x1) => x0.getComputedStyle(x1),
      _744: x0 => x0.screen,
      _745: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._745(f,arguments.length,x0) }),
      _746: (x0,x1) => x0.requestAnimationFrame(x1),
      _751: (x0,x1) => x0.warn(x1),
      _753: (x0,x1) => x0.debug(x1),
      _754: x0 => globalThis.parseFloat(x0),
      _755: () => globalThis.window,
      _756: () => globalThis.Intl,
      _757: () => globalThis.Symbol,
      _758: (x0,x1,x2,x3,x4) => globalThis.createImageBitmap(x0,x1,x2,x3,x4),
      _760: x0 => x0.clipboard,
      _761: x0 => x0.maxTouchPoints,
      _762: x0 => x0.vendor,
      _763: x0 => x0.language,
      _764: x0 => x0.platform,
      _765: x0 => x0.userAgent,
      _766: (x0,x1) => x0.vibrate(x1),
      _767: x0 => x0.languages,
      _768: x0 => x0.documentElement,
      _769: (x0,x1) => x0.querySelector(x1),
      _772: (x0,x1) => x0.createElement(x1),
      _775: (x0,x1) => x0.createEvent(x1),
      _776: x0 => x0.activeElement,
      _779: x0 => x0.head,
      _780: x0 => x0.body,
      _782: (x0,x1) => { x0.title = x1 },
      _785: x0 => x0.visibilityState,
      _786: () => globalThis.document,
      _787: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._787(f,arguments.length,x0) }),
      _788: (x0,x1) => x0.dispatchEvent(x1),
      _796: x0 => x0.target,
      _798: x0 => x0.timeStamp,
      _799: x0 => x0.type,
      _801: (x0,x1,x2,x3) => x0.initEvent(x1,x2,x3),
      _807: x0 => x0.baseURI,
      _808: x0 => x0.firstChild,
      _812: x0 => x0.parentElement,
      _814: (x0,x1) => { x0.textContent = x1 },
      _815: x0 => x0.parentNode,
      _816: x0 => x0.nextSibling,
      _817: (x0,x1) => x0.removeChild(x1),
      _818: x0 => x0.isConnected,
      _826: x0 => x0.clientHeight,
      _827: x0 => x0.clientWidth,
      _828: x0 => x0.offsetHeight,
      _829: x0 => x0.offsetWidth,
      _830: x0 => x0.id,
      _831: (x0,x1) => { x0.id = x1 },
      _834: (x0,x1) => { x0.spellcheck = x1 },
      _835: x0 => x0.tagName,
      _836: x0 => x0.style,
      _838: (x0,x1) => x0.querySelectorAll(x1),
      _839: (x0,x1,x2) => x0.setAttribute(x1,x2),
      _840: (x0,x1) => { x0.tabIndex = x1 },
      _841: x0 => x0.tabIndex,
      _842: (x0,x1) => x0.focus(x1),
      _843: x0 => x0.scrollTop,
      _844: (x0,x1) => { x0.scrollTop = x1 },
      _845: x0 => x0.scrollLeft,
      _846: (x0,x1) => { x0.scrollLeft = x1 },
      _847: x0 => x0.classList,
      _849: (x0,x1) => { x0.className = x1 },
      _851: (x0,x1) => x0.getElementsByClassName(x1),
      _852: x0 => x0.click(),
      _853: (x0,x1) => x0.attachShadow(x1),
      _856: x0 => x0.computedStyleMap(),
      _857: (x0,x1) => x0.get(x1),
      _863: (x0,x1) => x0.getPropertyValue(x1),
      _864: (x0,x1,x2,x3) => x0.setProperty(x1,x2,x3),
      _865: x0 => x0.offsetLeft,
      _866: x0 => x0.offsetTop,
      _867: x0 => x0.offsetParent,
      _869: (x0,x1) => { x0.name = x1 },
      _870: x0 => x0.content,
      _871: (x0,x1) => { x0.content = x1 },
      _875: (x0,x1) => { x0.src = x1 },
      _876: x0 => x0.naturalWidth,
      _877: x0 => x0.naturalHeight,
      _881: (x0,x1) => { x0.crossOrigin = x1 },
      _883: (x0,x1) => { x0.decoding = x1 },
      _884: x0 => x0.decode(),
      _889: (x0,x1) => { x0.nonce = x1 },
      _894: (x0,x1) => { x0.width = x1 },
      _896: (x0,x1) => { x0.height = x1 },
      _899: (x0,x1) => x0.getContext(x1),
      _960: x0 => x0.width,
      _961: x0 => x0.height,
      _963: (x0,x1) => x0.fetch(x1),
      _964: x0 => x0.status,
      _966: x0 => x0.body,
      _967: x0 => x0.arrayBuffer(),
      _969: x0 => x0.text(),
      _970: x0 => x0.read(),
      _971: x0 => x0.value,
      _972: x0 => x0.done,
      _979: x0 => x0.name,
      _980: x0 => x0.x,
      _981: x0 => x0.y,
      _984: x0 => x0.top,
      _985: x0 => x0.right,
      _986: x0 => x0.bottom,
      _987: x0 => x0.left,
      _997: x0 => x0.height,
      _998: x0 => x0.width,
      _999: x0 => x0.scale,
      _1000: (x0,x1) => { x0.value = x1 },
      _1003: (x0,x1) => { x0.placeholder = x1 },
      _1005: (x0,x1) => { x0.name = x1 },
      _1006: x0 => x0.selectionDirection,
      _1007: x0 => x0.selectionStart,
      _1008: x0 => x0.selectionEnd,
      _1011: x0 => x0.value,
      _1013: (x0,x1,x2) => x0.setSelectionRange(x1,x2),
      _1014: x0 => x0.readText(),
      _1015: (x0,x1) => x0.writeText(x1),
      _1017: x0 => x0.altKey,
      _1018: x0 => x0.code,
      _1019: x0 => x0.ctrlKey,
      _1020: x0 => x0.key,
      _1021: x0 => x0.keyCode,
      _1022: x0 => x0.location,
      _1023: x0 => x0.metaKey,
      _1024: x0 => x0.repeat,
      _1025: x0 => x0.shiftKey,
      _1026: x0 => x0.isComposing,
      _1028: x0 => x0.state,
      _1029: (x0,x1) => x0.go(x1),
      _1031: (x0,x1,x2,x3) => x0.pushState(x1,x2,x3),
      _1032: (x0,x1,x2,x3) => x0.replaceState(x1,x2,x3),
      _1033: x0 => x0.pathname,
      _1034: x0 => x0.search,
      _1035: x0 => x0.hash,
      _1039: x0 => x0.state,
      _1042: (x0,x1) => x0.createObjectURL(x1),
      _1044: x0 => new Blob(x0),
      _1046: x0 => new MutationObserver(x0),
      _1047: (x0,x1,x2) => x0.observe(x1,x2),
      _1048: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1048(f,arguments.length,x0,x1) }),
      _1051: x0 => x0.attributeName,
      _1052: x0 => x0.type,
      _1053: x0 => x0.matches,
      _1054: x0 => x0.matches,
      _1058: x0 => x0.relatedTarget,
      _1060: x0 => x0.clientX,
      _1061: x0 => x0.clientY,
      _1062: x0 => x0.offsetX,
      _1063: x0 => x0.offsetY,
      _1066: x0 => x0.button,
      _1067: x0 => x0.buttons,
      _1068: x0 => x0.ctrlKey,
      _1072: x0 => x0.pointerId,
      _1073: x0 => x0.pointerType,
      _1074: x0 => x0.pressure,
      _1075: x0 => x0.tiltX,
      _1076: x0 => x0.tiltY,
      _1077: x0 => x0.getCoalescedEvents(),
      _1080: x0 => x0.deltaX,
      _1081: x0 => x0.deltaY,
      _1082: x0 => x0.wheelDeltaX,
      _1083: x0 => x0.wheelDeltaY,
      _1084: x0 => x0.deltaMode,
      _1091: x0 => x0.changedTouches,
      _1094: x0 => x0.clientX,
      _1095: x0 => x0.clientY,
      _1098: x0 => x0.data,
      _1101: (x0,x1) => { x0.disabled = x1 },
      _1103: (x0,x1) => { x0.type = x1 },
      _1104: (x0,x1) => { x0.max = x1 },
      _1105: (x0,x1) => { x0.min = x1 },
      _1106: x0 => x0.value,
      _1107: (x0,x1) => { x0.value = x1 },
      _1108: x0 => x0.disabled,
      _1109: (x0,x1) => { x0.disabled = x1 },
      _1111: (x0,x1) => { x0.placeholder = x1 },
      _1112: (x0,x1) => { x0.name = x1 },
      _1115: (x0,x1) => { x0.autocomplete = x1 },
      _1116: x0 => x0.selectionDirection,
      _1117: x0 => x0.selectionStart,
      _1119: x0 => x0.selectionEnd,
      _1122: (x0,x1,x2) => x0.setSelectionRange(x1,x2),
      _1123: (x0,x1) => x0.add(x1),
      _1126: (x0,x1) => { x0.noValidate = x1 },
      _1127: (x0,x1) => { x0.method = x1 },
      _1128: (x0,x1) => { x0.action = x1 },
      _1129: (x0,x1) => new OffscreenCanvas(x0,x1),
      _1135: (x0,x1) => x0.getContext(x1),
      _1137: x0 => x0.convertToBlob(),
      _1154: x0 => x0.orientation,
      _1155: x0 => x0.width,
      _1156: x0 => x0.height,
      _1157: (x0,x1) => x0.lock(x1),
      _1176: x0 => new ResizeObserver(x0),
      _1179: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1179(f,arguments.length,x0,x1) }),
      _1187: x0 => x0.length,
      _1188: x0 => x0.iterator,
      _1189: x0 => x0.Segmenter,
      _1190: x0 => x0.v8BreakIterator,
      _1191: (x0,x1) => new Intl.Segmenter(x0,x1),
      _1194: x0 => x0.language,
      _1195: x0 => x0.script,
      _1196: x0 => x0.region,
      _1214: x0 => x0.done,
      _1215: x0 => x0.value,
      _1216: x0 => x0.index,
      _1220: (x0,x1) => new Intl.v8BreakIterator(x0,x1),
      _1221: (x0,x1) => x0.adoptText(x1),
      _1222: x0 => x0.first(),
      _1223: x0 => x0.next(),
      _1224: x0 => x0.current(),
      _1238: x0 => x0.hostElement,
      _1239: x0 => x0.viewConstraints,
      _1240: x0 => x0.initialData,
      _1242: x0 => x0.maxHeight,
      _1243: x0 => x0.maxWidth,
      _1244: x0 => x0.minHeight,
      _1245: x0 => x0.minWidth,
      _1246: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1246(f,arguments.length,x0) }),
      _1247: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1247(f,arguments.length,x0) }),
      _1248: (x0,x1) => ({addView: x0,removeView: x1}),
      _1251: x0 => x0.loader,
      _1252: () => globalThis._flutter,
      _1253: (x0,x1) => x0.didCreateEngineInitializer(x1),
      _1254: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1254(f,arguments.length,x0) }),
      _1255: f => finalizeWrapper(f, function() { return dartInstance.exports._1255(f,arguments.length) }),
      _1256: (x0,x1) => ({initializeEngine: x0,autoStart: x1}),
      _1259: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1259(f,arguments.length,x0) }),
      _1260: x0 => ({runApp: x0}),
      _1262: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1262(f,arguments.length,x0,x1) }),
      _1263: x0 => x0.length,
      _1264: () => globalThis.window.ImageDecoder,
      _1265: x0 => x0.tracks,
      _1267: x0 => x0.completed,
      _1269: x0 => x0.image,
      _1275: x0 => x0.displayWidth,
      _1276: x0 => x0.displayHeight,
      _1277: x0 => x0.duration,
      _1280: x0 => x0.ready,
      _1281: x0 => x0.selectedTrack,
      _1282: x0 => x0.repetitionCount,
      _1283: x0 => x0.frameCount,
      _1326: x0 => x0.requestFullscreen(),
      _1327: x0 => x0.exitFullscreen(),
      _1328: (x0,x1) => x0.append(x1),
      _1329: (x0,x1,x2) => x0.call(x1,x2),
      _1330: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1330(f,arguments.length,x0,x1) }),
      _1331: x0 => new ResizeObserver(x0),
      _1332: (x0,x1) => x0.observe(x1),
      _1333: (x0,x1,x2,x3) => x0.call(x1,x2,x3),
      _1337: (x0,x1) => x0.call(x1),
      _1338: (x0,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12,x13,x14,x15,x16,x17,x18,x19,x20) => x0.call(x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12,x13,x14,x15,x16,x17,x18,x19,x20),
      _1339: x0 => x0.call(),
      _1340: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1340(f,arguments.length,x0) }),
      _1341: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1341(f,arguments.length,x0) }),
      _1342: x0 => x0.call(),
      _1343: f => finalizeWrapper(f, function(x0,x1,x2,x3) { return dartInstance.exports._1343(f,arguments.length,x0,x1,x2,x3) }),
      _1344: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1344(f,arguments.length,x0) }),
      _1345: f => finalizeWrapper(f, function(x0,x1,x2) { return dartInstance.exports._1345(f,arguments.length,x0,x1,x2) }),
      _1346: f => finalizeWrapper(f, function(x0,x1,x2,x3) { return dartInstance.exports._1346(f,arguments.length,x0,x1,x2,x3) }),
      _1347: f => finalizeWrapper(f, function(x0,x1,x2,x3,x4,x5,x6,x7,x8) { return dartInstance.exports._1347(f,arguments.length,x0,x1,x2,x3,x4,x5,x6,x7,x8) }),
      _1348: f => finalizeWrapper(f, function(x0,x1,x2,x3,x4) { return dartInstance.exports._1348(f,arguments.length,x0,x1,x2,x3,x4) }),
      _1349: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1349(f,arguments.length,x0,x1) }),
      _1350: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1350(f,arguments.length,x0) }),
      _1351: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1351(f,arguments.length,x0) }),
      _1352: f => finalizeWrapper(f, function(x0,x1,x2,x3,x4,x5,x6) { return dartInstance.exports._1352(f,arguments.length,x0,x1,x2,x3,x4,x5,x6) }),
      _1353: f => finalizeWrapper(f, function(x0,x1,x2) { return dartInstance.exports._1353(f,arguments.length,x0,x1,x2) }),
      _1354: f => finalizeWrapper(f, function(x0,x1,x2) { return dartInstance.exports._1354(f,arguments.length,x0,x1,x2) }),
      _1355: f => finalizeWrapper(f, function(x0,x1,x2) { return dartInstance.exports._1355(f,arguments.length,x0,x1,x2) }),
      _1356: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1356(f,arguments.length,x0) }),
      _1357: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1357(f,arguments.length,x0) }),
      _1358: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1358(f,arguments.length,x0) }),
      _1359: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1359(f,arguments.length,x0) }),
      _1360: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1360(f,arguments.length,x0) }),
      _1361: (x0,x1,x2,x3,x4) => x0.call(x1,x2,x3,x4),
      _1362: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1362(f,arguments.length,x0,x1) }),
      _1363: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1363(f,arguments.length,x0,x1) }),
      _1364: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1364(f,arguments.length,x0,x1) }),
      _1365: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1365(f,arguments.length,x0,x1) }),
      _1366: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1366(f,arguments.length,x0,x1) }),
      _1367: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1367(f,arguments.length,x0,x1) }),
      _1368: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1368(f,arguments.length,x0,x1) }),
      _1369: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1369(f,arguments.length,x0,x1) }),
      _1370: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1370(f,arguments.length,x0,x1) }),
      _1371: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1371(f,arguments.length,x0,x1) }),
      _1372: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1372(f,arguments.length,x0) }),
      _1373: (x0,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12) => x0.call(x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12),
      _1374: (x0,x1,x2,x3,x4) => x0.call(x1,x2,x3,x4),
      _1376: (x0,x1,x2,x3,x4,x5) => x0.call(x1,x2,x3,x4,x5),
      _1377: (x0,x1,x2,x3,x4,x5,x6,x7,x8) => x0.call(x1,x2,x3,x4,x5,x6,x7,x8),
      _1385: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1385(f,arguments.length,x0) }),
      _1386: (x0,x1,x2,x3,x4,x5,x6) => x0.call(x1,x2,x3,x4,x5,x6),
      _1399: x0 => x0.createRange(),
      _1400: (x0,x1) => x0.selectNode(x1),
      _1401: x0 => x0.getSelection(),
      _1402: x0 => x0.removeAllRanges(),
      _1403: (x0,x1) => x0.addRange(x1),
      _1404: (x0,x1) => x0.createElement(x1),
      _1405: (x0,x1) => x0.append(x1),
      _1406: (x0,x1,x2) => x0.insertRule(x1,x2),
      _1407: (x0,x1) => x0.add(x1),
      _1408: x0 => x0.preventDefault(),
      _1409: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1409(f,arguments.length,x0) }),
      _1410: (x0,x1,x2) => x0.addEventListener(x1,x2),
      _1411: () => globalThis.window.navigator.userAgent,
      _1412: (x0,x1) => x0.get(x1),
      _1413: x0 => x0.text(),
      _1417: (x0,x1,x2,x3) => x0.addEventListener(x1,x2,x3),
      _1418: (x0,x1,x2,x3) => x0.removeEventListener(x1,x2,x3),
      _1419: (x0,x1) => x0.createElement(x1),
      _1420: (x0,x1,x2) => x0.setAttribute(x1,x2),
      _1426: (x0,x1,x2,x3) => x0.open(x1,x2,x3),
      _1427: (x0,x1) => x0.canShare(x1),
      _1428: (x0,x1) => x0.share(x1),
      _1429: x0 => ({url: x0}),
      _1430: (x0,x1,x2) => ({files: x0,title: x1,text: x2}),
      _1431: (x0,x1) => ({files: x0,text: x1}),
      _1432: (x0,x1) => ({files: x0,title: x1}),
      _1433: x0 => ({files: x0}),
      _1434: (x0,x1) => ({title: x0,text: x1}),
      _1435: x0 => ({text: x0}),
      _1436: x0 => x0.click(),
      _1437: x0 => x0.remove(),
      _1438: () => ({}),
      _1439: (x0,x1,x2) => new File(x0,x1,x2),
      _1440: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1440(f,arguments.length,x0) }),
      _1441: (x0,x1,x2) => globalThis.jsConnect(x0,x1,x2),
      _1442: (x0,x1) => globalThis.jsSend(x0,x1),
      _1443: x0 => globalThis.jsDisconnect(x0),
      _1444: x0 => ({audio: x0}),
      _1445: (x0,x1) => x0.getUserMedia(x1),
      _1446: x0 => x0.getAudioTracks(),
      _1447: x0 => x0.stop(),
      _1448: (x0,x1) => x0.removeTrack(x1),
      _1449: x0 => x0.close(),
      _1450: (x0,x1) => x0.warn(x1),
      _1451: x0 => x0.getSettings(),
      _1452: x0 => ({sampleRate: x0}),
      _1453: x0 => new AudioContext(x0),
      _1454: () => new AudioContext(),
      _1455: x0 => x0.suspend(),
      _1456: x0 => x0.resume(),
      _1457: (x0,x1) => x0.connect(x1),
      _1458: x0 => globalThis.URL.createObjectURL(x0),
      _1459: (x0,x1) => x0.createMediaStreamSource(x1),
      _1460: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1460(f,arguments.length,x0) }),
      _1461: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1461(f,arguments.length,x0) }),
      _1462: (x0,x1) => x0.addModule(x1),
      _1463: x0 => ({parameterData: x0}),
      _1464: (x0,x1,x2) => new AudioWorkletNode(x0,x1,x2),
      _1465: x0 => x0.enumerateDevices(),
      _1466: x0 => globalThis.URL.revokeObjectURL(x0),
      _1467: x0 => x0.pause(),
      _1468: x0 => x0.resume(),
      _1469: x0 => x0.disconnect(),
      _1470: x0 => x0.stop(),
      _1471: (x0,x1,x2) => ({mimeType: x0,audioBitsPerSecond: x1,bitsPerSecond: x2}),
      _1472: (x0,x1) => new MediaRecorder(x0,x1),
      _1473: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1473(f,arguments.length,x0) }),
      _1474: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1474(f,arguments.length,x0) }),
      _1475: (x0,x1) => x0.start(x1),
      _1476: x0 => ({type: x0}),
      _1477: (x0,x1) => new Blob(x0,x1),
      _1478: (x0,x1) => globalThis.jsFixWebmDuration(x0,x1),
      _1479: x0 => x0.createAnalyser(),
      _1480: (x0,x1) => x0.getFloatFrequencyData(x1),
      _1481: x0 => globalThis.MediaRecorder.isTypeSupported(x0),
      _1482: x0 => x0.decode(),
      _1483: (x0,x1,x2,x3) => x0.open(x1,x2,x3),
      _1484: (x0,x1,x2) => x0.setRequestHeader(x1,x2),
      _1485: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1485(f,arguments.length,x0) }),
      _1486: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1486(f,arguments.length,x0) }),
      _1487: x0 => x0.send(),
      _1488: () => new XMLHttpRequest(),
      _1489: x0 => globalThis.Wakelock.toggle(x0),
      _1490: () => globalThis.Wakelock.enabled(),
      _1491: (x0,x1) => x0.createMediaElementSource(x1),
      _1492: x0 => x0.createStereoPanner(),
      _1493: x0 => x0.load(),
      _1494: x0 => x0.play(),
      _1495: x0 => x0.pause(),
      _1496: (x0,x1) => x0.query(x1),
      _1497: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1497(f,arguments.length,x0) }),
      _1498: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1498(f,arguments.length,x0) }),
      _1499: (x0,x1,x2) => ({enableHighAccuracy: x0,timeout: x1,maximumAge: x2}),
      _1500: (x0,x1,x2,x3) => x0.getCurrentPosition(x1,x2,x3),
      _1501: (x0,x1) => x0.clearWatch(x1),
      _1502: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1502(f,arguments.length,x0) }),
      _1503: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1503(f,arguments.length,x0) }),
      _1504: (x0,x1,x2,x3) => x0.watchPosition(x1,x2,x3),
      _1505: (x0,x1) => x0.getItem(x1),
      _1506: (x0,x1) => x0.removeItem(x1),
      _1507: (x0,x1,x2) => x0.setItem(x1,x2),
      _1508: x0 => ({frequency: x0}),
      _1509: x0 => new Accelerometer(x0),
      _1510: x0 => x0.start(),
      _1511: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1511(f,arguments.length,x0) }),
      _1512: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1512(f,arguments.length,x0) }),
      _1513: x0 => new Gyroscope(x0),
      _1514: x0 => x0.start(),
      _1515: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1515(f,arguments.length,x0) }),
      _1516: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1516(f,arguments.length,x0) }),
      _1517: x0 => new LinearAccelerationSensor(x0),
      _1518: x0 => x0.start(),
      _1519: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1519(f,arguments.length,x0) }),
      _1520: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1520(f,arguments.length,x0) }),
      _1521: x0 => new Magnetometer(x0),
      _1522: x0 => x0.start(),
      _1523: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1523(f,arguments.length,x0) }),
      _1524: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1524(f,arguments.length,x0) }),
      _1525: x0 => ({name: x0}),
      _1526: x0 => ({video: x0}),
      _1527: x0 => x0.getVideoTracks(),
      _1528: () => globalThis.Notification.requestPermission(),
      _1529: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1529(f,arguments.length,x0) }),
      _1530: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1530(f,arguments.length,x0) }),
      _1531: (x0,x1,x2) => x0.getCurrentPosition(x1,x2),
      _1534: (x0,x1) => x0.querySelector(x1),
      _1535: (x0,x1) => x0.item(x1),
      _1536: () => new FileReader(),
      _1538: (x0,x1) => x0.readAsArrayBuffer(x1),
      _1539: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1539(f,arguments.length,x0) }),
      _1540: (x0,x1,x2) => x0.removeEventListener(x1,x2),
      _1541: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1541(f,arguments.length,x0) }),
      _1542: (x0,x1,x2) => x0.addEventListener(x1,x2),
      _1543: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1543(f,arguments.length,x0) }),
      _1544: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1544(f,arguments.length,x0) }),
      _1545: (x0,x1) => x0.removeChild(x1),
      _1546: x0 => new Blob(x0),
      _1547: (x0,x1,x2) => x0.slice(x1,x2),
      _1548: x0 => x0.deviceMemory,
      _1549: x0 => x0.getBattery(),
      _1550: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1550(f,arguments.length,x0) }),
      _1551: (x0,x1) => x0.key(x1),
      _1552: (x0,x1,x2,x3,x4,x5,x6,x7) => x0.unwrapKey(x1,x2,x3,x4,x5,x6,x7),
      _1553: (x0,x1,x2,x3,x4,x5) => x0.importKey(x1,x2,x3,x4,x5),
      _1554: (x0,x1,x2,x3) => x0.generateKey(x1,x2,x3),
      _1555: (x0,x1,x2,x3,x4) => x0.wrapKey(x1,x2,x3,x4),
      _1556: (x0,x1,x2) => x0.exportKey(x1,x2),
      _1557: (x0,x1) => x0.getRandomValues(x1),
      _1558: (x0,x1,x2,x3) => x0.encrypt(x1,x2,x3),
      _1559: (x0,x1,x2,x3) => x0.decrypt(x1,x2,x3),
      _1561: (x0,x1) => x0.matchMedia(x1),
      _1564: x0 => x0.pyodide,
      _1565: x0 => x0.multiView,
      _1567: x0 => x0.webSocketEndpoint,
      _1568: x0 => x0.routeUrlStrategy,
      _1573: () => globalThis.flet,
      _1574: Date.now,
      _1576: s => new Date(s * 1000).getTimezoneOffset() * 60,
      _1577: s => {
        if (!/^\s*[+-]?(?:Infinity|NaN|(?:\.\d+|\d+(?:\.\d*)?)(?:[eE][+-]?\d+)?)\s*$/.test(s)) {
          return NaN;
        }
        return parseFloat(s);
      },
      _1578: () => {
        let stackString = new Error().stack.toString();
        let frames = stackString.split('\n');
        let drop = 2;
        if (frames[0] === 'Error') {
            drop += 1;
        }
        return frames.slice(drop).join('\n');
      },
      _1579: () => typeof dartUseDateNowForTicks !== "undefined",
      _1580: () => 1000 * performance.now(),
      _1581: () => Date.now(),
      _1582: () => {
        // On browsers return `globalThis.location.href`
        if (globalThis.location != null) {
          return globalThis.location.href;
        }
        return null;
      },
      _1583: () => {
        return typeof process != "undefined" &&
               Object.prototype.toString.call(process) == "[object process]" &&
               process.platform == "win32"
      },
      _1584: () => new WeakMap(),
      _1585: (map, o) => map.get(o),
      _1586: (map, o, v) => map.set(o, v),
      _1587: x0 => new WeakRef(x0),
      _1588: x0 => x0.deref(),
      _1589: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1589(f,arguments.length,x0) }),
      _1590: x0 => new FinalizationRegistry(x0),
      _1591: (x0,x1,x2,x3) => x0.register(x1,x2,x3),
      _1592: (x0,x1,x2) => x0.register(x1,x2),
      _1593: (x0,x1) => x0.unregister(x1),
      _1595: () => globalThis.WeakRef,
      _1596: () => globalThis.FinalizationRegistry,
      _1598: s => JSON.stringify(s),
      _1599: s => printToConsole(s),
      _1600: (o, p, r) => o.replaceAll(p, () => r),
      _1601: (o, p, r) => o.replace(p, () => r),
      _1602: Function.prototype.call.bind(String.prototype.toLowerCase),
      _1603: s => s.toUpperCase(),
      _1604: s => s.trim(),
      _1605: s => s.trimLeft(),
      _1606: s => s.trimRight(),
      _1607: (string, times) => string.repeat(times),
      _1608: Function.prototype.call.bind(String.prototype.indexOf),
      _1609: (s, p, i) => s.lastIndexOf(p, i),
      _1610: (string, token) => string.split(token),
      _1611: Object.is,
      _1612: o => o instanceof Array,
      _1613: (a, i) => a.push(i),
      _1614: (a, i) => a.splice(i, 1)[0],
      _1615: (a, i, v) => a.splice(i, 0, v),
      _1616: (a, l) => a.length = l,
      _1617: a => a.pop(),
      _1618: (a, i) => a.splice(i, 1),
      _1619: (a, s) => a.join(s),
      _1620: (a, s, e) => a.slice(s, e),
      _1621: (a, s, e) => a.splice(s, e),
      _1622: (a, b) => a == b ? 0 : (a > b ? 1 : -1),
      _1623: a => a.length,
      _1624: (a, l) => a.length = l,
      _1625: (a, i) => a[i],
      _1626: (a, i, v) => a[i] = v,
      _1628: o => {
        if (o instanceof ArrayBuffer) return 0;
        if (globalThis.SharedArrayBuffer !== undefined &&
            o instanceof SharedArrayBuffer) {
          return 1;
        }
        return 2;
      },
      _1629: (o, offsetInBytes, lengthInBytes) => {
        var dst = new ArrayBuffer(lengthInBytes);
        new Uint8Array(dst).set(new Uint8Array(o, offsetInBytes, lengthInBytes));
        return new DataView(dst);
      },
      _1630: o => o instanceof DataView,
      _1631: o => o instanceof Uint8Array,
      _1632: (o, start, length) => new Uint8Array(o.buffer, o.byteOffset + start, length),
      _1633: o => o instanceof Int8Array,
      _1634: (o, start, length) => new Int8Array(o.buffer, o.byteOffset + start, length),
      _1635: o => o instanceof Uint8ClampedArray,
      _1636: (o, start, length) => new Uint8ClampedArray(o.buffer, o.byteOffset + start, length),
      _1637: o => o instanceof Uint16Array,
      _1638: (o, start, length) => new Uint16Array(o.buffer, o.byteOffset + start, length),
      _1639: o => o instanceof Int16Array,
      _1640: (o, start, length) => new Int16Array(o.buffer, o.byteOffset + start, length),
      _1641: o => o instanceof Uint32Array,
      _1642: (o, start, length) => new Uint32Array(o.buffer, o.byteOffset + start, length),
      _1643: o => o instanceof Int32Array,
      _1644: (o, start, length) => new Int32Array(o.buffer, o.byteOffset + start, length),
      _1646: (o, start, length) => new BigInt64Array(o.buffer, o.byteOffset + start, length),
      _1647: o => o instanceof Float32Array,
      _1648: (o, start, length) => new Float32Array(o.buffer, o.byteOffset + start, length),
      _1649: o => o instanceof Float64Array,
      _1650: (o, start, length) => new Float64Array(o.buffer, o.byteOffset + start, length),
      _1651: (t, s) => t.set(s),
      _1652: l => new DataView(new ArrayBuffer(l)),
      _1653: (o) => new DataView(o.buffer, o.byteOffset, o.byteLength),
      _1654: o => o.byteLength,
      _1655: o => o.buffer,
      _1656: o => o.byteOffset,
      _1657: Function.prototype.call.bind(Object.getOwnPropertyDescriptor(DataView.prototype, 'byteLength').get),
      _1658: (b, o) => new DataView(b, o),
      _1659: (b, o, l) => new DataView(b, o, l),
      _1660: Function.prototype.call.bind(DataView.prototype.getUint8),
      _1661: Function.prototype.call.bind(DataView.prototype.setUint8),
      _1662: Function.prototype.call.bind(DataView.prototype.getInt8),
      _1663: Function.prototype.call.bind(DataView.prototype.setInt8),
      _1664: Function.prototype.call.bind(DataView.prototype.getUint16),
      _1665: Function.prototype.call.bind(DataView.prototype.setUint16),
      _1666: Function.prototype.call.bind(DataView.prototype.getInt16),
      _1667: Function.prototype.call.bind(DataView.prototype.setInt16),
      _1668: Function.prototype.call.bind(DataView.prototype.getUint32),
      _1669: Function.prototype.call.bind(DataView.prototype.setUint32),
      _1670: Function.prototype.call.bind(DataView.prototype.getInt32),
      _1671: Function.prototype.call.bind(DataView.prototype.setInt32),
      _1672: Function.prototype.call.bind(DataView.prototype.getBigUint64),
      _1674: Function.prototype.call.bind(DataView.prototype.getBigInt64),
      _1675: Function.prototype.call.bind(DataView.prototype.setBigInt64),
      _1676: Function.prototype.call.bind(DataView.prototype.getFloat32),
      _1677: Function.prototype.call.bind(DataView.prototype.setFloat32),
      _1678: Function.prototype.call.bind(DataView.prototype.getFloat64),
      _1679: Function.prototype.call.bind(DataView.prototype.setFloat64),
      _1692: (ms, c) =>
      setTimeout(() => dartInstance.exports.$invokeCallback(c),ms),
      _1693: (handle) => clearTimeout(handle),
      _1694: (ms, c) =>
      setInterval(() => dartInstance.exports.$invokeCallback(c), ms),
      _1695: (handle) => clearInterval(handle),
      _1696: (c) =>
      queueMicrotask(() => dartInstance.exports.$invokeCallback(c)),
      _1697: () => Date.now(),
      _1698: (s, m) => {
        try {
          return new RegExp(s, m);
        } catch (e) {
          return String(e);
        }
      },
      _1699: (x0,x1) => x0.exec(x1),
      _1700: (x0,x1) => x0.test(x1),
      _1701: x0 => x0.pop(),
      _1703: o => o === undefined,
      _1705: o => typeof o === 'function' && o[jsWrappedDartFunctionSymbol] === true,
      _1707: o => {
        const proto = Object.getPrototypeOf(o);
        return proto === Object.prototype || proto === null;
      },
      _1708: o => o instanceof RegExp,
      _1709: (l, r) => l === r,
      _1710: o => o,
      _1711: o => o,
      _1712: o => o,
      _1713: b => !!b,
      _1714: o => o.length,
      _1716: (o, i) => o[i],
      _1717: f => f.dartFunction,
      _1718: () => ({}),
      _1719: () => [],
      _1721: () => globalThis,
      _1722: (constructor, args) => {
        const factoryFunction = constructor.bind.apply(
            constructor, [null, ...args]);
        return new factoryFunction();
      },
      _1723: (o, p) => p in o,
      _1724: (o, p) => o[p],
      _1725: (o, p, v) => o[p] = v,
      _1726: (o, m, a) => o[m].apply(o, a),
      _1728: o => String(o),
      _1729: (p, s, f) => p.then(s, (e) => f(e, e === undefined)),
      _1730: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1730(f,arguments.length,x0) }),
      _1731: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1731(f,arguments.length,x0,x1) }),
      _1732: o => {
        if (o === undefined) return 1;
        var type = typeof o;
        if (type === 'boolean') return 2;
        if (type === 'number') return 3;
        if (type === 'string') return 4;
        if (o instanceof Array) return 5;
        if (ArrayBuffer.isView(o)) {
          if (o instanceof Int8Array) return 6;
          if (o instanceof Uint8Array) return 7;
          if (o instanceof Uint8ClampedArray) return 8;
          if (o instanceof Int16Array) return 9;
          if (o instanceof Uint16Array) return 10;
          if (o instanceof Int32Array) return 11;
          if (o instanceof Uint32Array) return 12;
          if (o instanceof Float32Array) return 13;
          if (o instanceof Float64Array) return 14;
          if (o instanceof DataView) return 15;
        }
        if (o instanceof ArrayBuffer) return 16;
        // Feature check for `SharedArrayBuffer` before doing a type-check.
        if (globalThis.SharedArrayBuffer !== undefined &&
            o instanceof SharedArrayBuffer) {
            return 17;
        }
        if (o instanceof Promise) return 18;
        return 19;
      },
      _1733: o => [o],
      _1734: (o0, o1) => [o0, o1],
      _1735: (o0, o1, o2) => [o0, o1, o2],
      _1736: (o0, o1, o2, o3) => [o0, o1, o2, o3],
      _1737: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmI8ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1738: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmI8ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1739: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmI16ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1740: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmI16ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1741: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmI32ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1742: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmI32ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1743: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmF32ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1744: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmF32ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1745: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmF64ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1746: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmF64ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1747: x0 => new ArrayBuffer(x0),
      _1748: s => {
        if (/[[\]{}()*+?.\\^$|]/.test(s)) {
            s = s.replace(/[[\]{}()*+?.\\^$|]/g, '\\$&');
        }
        return s;
      },
      _1749: x0 => x0.input,
      _1750: x0 => x0.index,
      _1751: x0 => x0.groups,
      _1752: x0 => x0.flags,
      _1753: x0 => x0.multiline,
      _1754: x0 => x0.ignoreCase,
      _1755: x0 => x0.unicode,
      _1756: x0 => x0.dotAll,
      _1757: (x0,x1) => { x0.lastIndex = x1 },
      _1758: (o, p) => p in o,
      _1759: (o, p) => o[p],
      _1760: (o, p, v) => o[p] = v,
      _1761: (o, p) => delete o[p],
      _1762: (x0,x1) => x0.end(x1),
      _1763: (x0,x1) => x0.item(x1),
      _1764: (x0,x1) => x0.appendChild(x1),
      _1767: (x0,x1,x2) => x0.setRequestHeader(x1,x2),
      _1768: f => finalizeWrapper(f, function(x0,x1) { return dartInstance.exports._1768(f,arguments.length,x0,x1) }),
      _1769: x0 => ({xhrSetup: x0}),
      _1770: x0 => new Hls(x0),
      _1771: (x0,x1) => x0.loadSource(x1),
      _1772: (x0,x1) => x0.attachMedia(x1),
      _1773: (x0,x1) => x0.canPlayType(x1),
      _1774: () => globalThis.Hls.isSupported(),
      _1775: () => new XMLHttpRequest(),
      _1776: (x0,x1,x2,x3) => x0.open(x1,x2,x3),
      _1779: x0 => x0.send(),
      _1781: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1781(f,arguments.length,x0) }),
      _1782: f => finalizeWrapper(f, function(x0) { return dartInstance.exports._1782(f,arguments.length,x0) }),
      _1787: (x0,x1) => new WebSocket(x0,x1),
      _1788: (x0,x1) => x0.send(x1),
      _1789: (x0,x1,x2) => x0.close(x1,x2),
      _1791: x0 => x0.close(),
      _1794: (x0,x1) => x0.append(x1),
      _1796: () => new AbortController(),
      _1797: x0 => x0.abort(),
      _1798: (x0,x1,x2,x3,x4,x5) => ({method: x0,headers: x1,body: x2,credentials: x3,redirect: x4,signal: x5}),
      _1799: (x0,x1) => globalThis.fetch(x0,x1),
      _1800: f => finalizeWrapper(f, function(x0,x1,x2) { return dartInstance.exports._1800(f,arguments.length,x0,x1,x2) }),
      _1801: (x0,x1) => x0.forEach(x1),
      _1802: x0 => x0.getReader(),
      _1803: x0 => x0.cancel(),
      _1804: x0 => x0.read(),
      _1805: (x0,x1,x2,x3) => ({method: x0,headers: x1,body: x2,credentials: x3}),
      _1806: (x0,x1,x2) => x0.fetch(x1,x2),
      _1807: x0 => x0.random(),
      _1808: (x0,x1) => x0.getRandomValues(x1),
      _1809: () => globalThis.crypto,
      _1810: () => globalThis.Math,
      _1819: Function.prototype.call.bind(Number.prototype.toString),
      _1820: Function.prototype.call.bind(BigInt.prototype.toString),
      _1821: Function.prototype.call.bind(Number.prototype.toString),
      _1822: (d, digits) => d.toFixed(digits),
      _1826: () => globalThis.document,
      _1827: () => globalThis.window,
      _1832: (x0,x1) => { x0.height = x1 },
      _1834: (x0,x1) => { x0.width = x1 },
      _1837: x0 => x0.head,
      _1838: x0 => x0.classList,
      _1842: (x0,x1) => { x0.innerText = x1 },
      _1843: x0 => x0.style,
      _1845: x0 => x0.sheet,
      _1846: x0 => x0.src,
      _1847: (x0,x1) => { x0.src = x1 },
      _1848: x0 => x0.naturalWidth,
      _1849: x0 => x0.naturalHeight,
      _1856: x0 => x0.offsetX,
      _1857: x0 => x0.offsetY,
      _1858: x0 => x0.button,
      _1865: x0 => x0.status,
      _1866: (x0,x1) => { x0.responseType = x1 },
      _1868: x0 => x0.response,
      _1917: (x0,x1) => { x0.responseType = x1 },
      _1918: x0 => x0.response,
      _1978: (x0,x1) => { x0.draggable = x1 },
      _1994: x0 => x0.style,
      _2351: (x0,x1) => { x0.target = x1 },
      _2353: (x0,x1) => { x0.download = x1 },
      _2378: (x0,x1) => { x0.href = x1 },
      _2471: (x0,x1) => { x0.src = x1 },
      _2566: x0 => x0.videoWidth,
      _2567: x0 => x0.videoHeight,
      _2579: (x0,x1) => { x0.kind = x1 },
      _2581: (x0,x1) => { x0.src = x1 },
      _2583: (x0,x1) => { x0.srclang = x1 },
      _2585: (x0,x1) => { x0.label = x1 },
      _2596: x0 => x0.error,
      _2598: (x0,x1) => { x0.src = x1 },
      _2603: (x0,x1) => { x0.crossOrigin = x1 },
      _2606: (x0,x1) => { x0.preload = x1 },
      _2607: x0 => x0.buffered,
      _2610: x0 => x0.currentTime,
      _2611: (x0,x1) => { x0.currentTime = x1 },
      _2612: x0 => x0.duration,
      _2613: x0 => x0.paused,
      _2616: x0 => x0.playbackRate,
      _2617: (x0,x1) => { x0.playbackRate = x1 },
      _2626: (x0,x1) => { x0.loop = x1 },
      _2628: (x0,x1) => { x0.controls = x1 },
      _2629: x0 => x0.volume,
      _2630: (x0,x1) => { x0.volume = x1 },
      _2631: x0 => x0.muted,
      _2632: (x0,x1) => { x0.muted = x1 },
      _2637: x0 => x0.textTracks,
      _2647: x0 => x0.code,
      _2648: x0 => x0.message,
      _2682: (x0,x1) => x0[x1],
      _2684: x0 => x0.length,
      _2699: (x0,x1) => { x0.mode = x1 },
      _2701: x0 => x0.activeCues,
      _2722: x0 => x0.length,
      _2918: (x0,x1) => { x0.accept = x1 },
      _2932: x0 => x0.files,
      _2958: (x0,x1) => { x0.multiple = x1 },
      _2976: (x0,x1) => { x0.type = x1 },
      _3225: x0 => x0.src,
      _3226: (x0,x1) => { x0.src = x1 },
      _3228: (x0,x1) => { x0.type = x1 },
      _3232: (x0,x1) => { x0.async = x1 },
      _3234: (x0,x1) => { x0.defer = x1 },
      _3246: (x0,x1) => { x0.charset = x1 },
      _3272: (x0,x1) => { x0.width = x1 },
      _3274: (x0,x1) => { x0.height = x1 },
      _3695: () => globalThis.window,
      _3755: x0 => x0.navigator,
      _3759: x0 => x0.screen,
      _3762: x0 => x0.innerHeight,
      _3766: x0 => x0.screenLeft,
      _3770: x0 => x0.outerHeight,
      _3771: x0 => x0.devicePixelRatio,
      _4010: x0 => x0.isSecureContext,
      _4013: x0 => x0.crypto,
      _4018: x0 => x0.sessionStorage,
      _4019: x0 => x0.localStorage,
      _4122: x0 => x0.geolocation,
      _4125: x0 => x0.mediaDevices,
      _4127: x0 => x0.permissions,
      _4128: x0 => x0.maxTouchPoints,
      _4135: x0 => x0.appCodeName,
      _4136: x0 => x0.appName,
      _4137: x0 => x0.appVersion,
      _4138: x0 => x0.platform,
      _4139: x0 => x0.product,
      _4140: x0 => x0.productSub,
      _4141: x0 => x0.userAgent,
      _4142: x0 => x0.vendor,
      _4143: x0 => x0.vendorSub,
      _4145: x0 => x0.language,
      _4146: x0 => x0.languages,
      _4147: x0 => x0.onLine,
      _4152: x0 => x0.hardwareConcurrency,
      _4192: x0 => x0.data,
      _4229: (x0,x1) => { x0.onmessage = x1 },
      _4349: x0 => x0.length,
      _4566: x0 => x0.readyState,
      _4575: x0 => x0.protocol,
      _4579: (x0,x1) => { x0.binaryType = x1 },
      _4582: x0 => x0.code,
      _4583: x0 => x0.reason,
      _5733: x0 => x0.destination,
      _5737: x0 => x0.state,
      _5738: x0 => x0.audioWorklet,
      _5840: (x0,x1) => { x0.fftSize = x1 },
      _5841: x0 => x0.frequencyBinCount,
      _5843: (x0,x1) => { x0.minDecibels = x1 },
      _5845: (x0,x1) => { x0.maxDecibels = x1 },
      _5847: (x0,x1) => { x0.smoothingTimeConstant = x1 },
      _6101: x0 => x0.port,
      _6240: x0 => x0.type,
      _6281: x0 => x0.signal,
      _6293: x0 => x0.length,
      _6337: x0 => x0.isConnected,
      _6342: x0 => x0.firstChild,
      _6353: () => globalThis.document,
      _6412: x0 => x0.documentElement,
      _6433: x0 => x0.body,
      _6435: x0 => x0.head,
      _6763: x0 => x0.id,
      _6764: (x0,x1) => { x0.id = x1 },
      _6788: (x0,x1) => { x0.innerHTML = x1 },
      _6791: x0 => x0.children,
      _8109: x0 => x0.value,
      _8111: x0 => x0.done,
      _8290: x0 => x0.size,
      _8291: x0 => x0.type,
      _8294: (x0,x1) => { x0.type = x1 },
      _8297: x0 => x0.name,
      _8303: x0 => x0.length,
      _8308: x0 => x0.result,
      _8677: x0 => x0.mimeType,
      _8678: x0 => x0.state,
      _8682: (x0,x1) => { x0.onstop = x1 },
      _8684: (x0,x1) => { x0.ondataavailable = x1 },
      _8709: x0 => x0.data,
      _8798: x0 => x0.url,
      _8800: x0 => x0.status,
      _8802: x0 => x0.statusText,
      _8803: x0 => x0.headers,
      _8804: x0 => x0.body,
      _9086: x0 => x0.matches,
      _9099: x0 => x0.width,
      _9100: x0 => x0.height,
      _9190: x0 => x0.state,
      _9590: x0 => x0.active,
      _9849: x0 => x0.sampleRate,
      _9861: x0 => x0.channelCount,
      _9923: x0 => x0.deviceId,
      _9924: x0 => x0.kind,
      _9925: x0 => x0.label,
      _10499: x0 => x0.coords,
      _10500: x0 => x0.timestamp,
      _10502: x0 => x0.accuracy,
      _10503: x0 => x0.latitude,
      _10504: x0 => x0.longitude,
      _10505: x0 => x0.altitude,
      _10506: x0 => x0.altitudeAccuracy,
      _10507: x0 => x0.heading,
      _10508: x0 => x0.speed,
      _10509: x0 => x0.code,
      _10510: x0 => x0.message,
      _10918: (x0,x1) => { x0.border = x1 },
      _11196: (x0,x1) => { x0.display = x1 },
      _11360: (x0,x1) => { x0.height = x1 },
      _12050: (x0,x1) => { x0.width = x1 },
      _12341: x0 => x0.charging,
      _12344: x0 => x0.level,
      _12346: (x0,x1) => { x0.onchargingchange = x1 },
      _12418: x0 => x0.name,
      _12419: x0 => x0.message,
      _12422: x0 => x0.subtle,
      _13128: () => globalThis.console,
      _13152: x0 => x0.x,
      _13153: x0 => x0.y,
      _13154: x0 => x0.z,
      _13155: (x0,x1) => { x0.onreading = x1 },
      _13156: (x0,x1) => { x0.onerror = x1 },
      _13157: x0 => x0.x,
      _13158: x0 => x0.y,
      _13159: x0 => x0.z,
      _13160: (x0,x1) => { x0.onreading = x1 },
      _13161: (x0,x1) => { x0.onerror = x1 },
      _13162: x0 => x0.x,
      _13163: x0 => x0.y,
      _13164: x0 => x0.z,
      _13165: (x0,x1) => { x0.onreading = x1 },
      _13166: (x0,x1) => { x0.onerror = x1 },
      _13167: x0 => x0.x,
      _13168: x0 => x0.y,
      _13169: x0 => x0.z,
      _13170: (x0,x1) => { x0.onreading = x1 },
      _13171: (x0,x1) => { x0.onerror = x1 },
      _13172: x0 => x0.error,
      _13173: x0 => x0.name,
      _13174: x0 => x0.message,

    };

    const baseImports = {
      dart2wasm: dart2wasm,
      Math: Math,
      Date: Date,
      Object: Object,
      Array: Array,
      Reflect: Reflect,
      S: new Proxy({}, { get(_, prop) { return prop; } }),

    };

    const jsStringPolyfill = {
      "charCodeAt": (s, i) => s.charCodeAt(i),
      "compare": (s1, s2) => {
        if (s1 < s2) return -1;
        if (s1 > s2) return 1;
        return 0;
      },
      "concat": (s1, s2) => s1 + s2,
      "equals": (s1, s2) => s1 === s2,
      "fromCharCode": (i) => String.fromCharCode(i),
      "length": (s) => s.length,
      "substring": (s, a, b) => s.substring(a, b),
      "fromCharCodeArray": (a, start, end) => {
        if (end <= start) return '';

        const read = dartInstance.exports.$wasmI16ArrayGet;
        let result = '';
        let index = start;
        const chunkLength = Math.min(end - index, 500);
        let array = new Array(chunkLength);
        while (index < end) {
          const newChunkLength = Math.min(end - index, 500);
          for (let i = 0; i < newChunkLength; i++) {
            array[i] = read(a, index++);
          }
          if (newChunkLength < chunkLength) {
            array = array.slice(0, newChunkLength);
          }
          result += String.fromCharCode(...array);
        }
        return result;
      },
      "intoCharCodeArray": (s, a, start) => {
        if (s === '') return 0;

        const write = dartInstance.exports.$wasmI16ArraySet;
        for (var i = 0; i < s.length; ++i) {
          write(a, start++, s.charCodeAt(i));
        }
        return s.length;
      },
      "test": (s) => typeof s == "string",
    };


    

    dartInstance = await WebAssembly.instantiate(this.module, {
      ...baseImports,
      ...additionalImports,
      
      "wasm:js-string": jsStringPolyfill,
    });

    return new InstantiatedApp(this, dartInstance);
  }
}

class InstantiatedApp {
  constructor(compiledApp, instantiatedModule) {
    this.compiledApp = compiledApp;
    this.instantiatedModule = instantiatedModule;
  }

  // Call the main function with the given arguments.
  invokeMain(...args) {
    this.instantiatedModule.exports.$invokeMain(args);
  }
}
