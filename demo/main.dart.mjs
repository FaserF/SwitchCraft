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
  // `loadDeferredModules` is a JS function that takes an array of module names
  //   matching wasm files produced by the dart2wasm compiler. It also takes a
  //   callback that should be invoked for each loaded module with 2 arugments:
  //   (1) the module name, (2) the loaded module in a format supported by
  //   `WebAssembly.compile` or `WebAssembly.compileStreaming`. The callback
  //   returns a Promise that resolves when the module is instantiated.
  //   loadDeferredModules should return a Promise that resolves when all the
  //   modules have been loaded and the callback promises have resolved.
  // `loadDeferredId` is a JS function that takes load ID produced by the
  //   compiler when the `load-ids` option is passed. Each load ID maps to one
  //   or more wasm files as specified in the emitted JSON file. It also takes a
  //   callback that should be invoked for each loaded module with 2 arugments:
  //   (1) the module name, (2) the loaded module in a format supported by
  //   `WebAssembly.compile` or `WebAssembly.compileStreaming`. The callback
  //   returns a Promise that resolves when the module is instantiated.
  //   loadDeferredModules should return a Promise that resolves when all the
  //   modules have been loaded and the callback promises have resolved.
  // `loadDynamicModule` is a JS function that takes two string names matching,
  //   in order, a wasm file produced by the dart2wasm compiler during dynamic
  //   module compilation and a corresponding js file produced by the same
  //   compilation. It also takes a callback that should be invoked with the
  //   loaded module in a format supported by `WebAssembly.compile` or
  //   `WebAssembly.compileStreaming` and the result of using the JS 'import'
  //   API on the js file path. It should return a Promise that resolves when
  //   all the modules have been loaded and the callback promises have resolved.
  async instantiate(additionalImports,
      {loadDeferredModules, loadDynamicModule, loadDeferredId} = {}) {
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
            _1: (decoder, codeUnits) => decoder.decode(codeUnits),
      _2: () => new TextDecoder("utf-8", {fatal: true}),
      _3: () => new TextDecoder("utf-8", {fatal: false}),
      _4: (s) => +s,
      _5: x0 => new Uint8Array(x0),
      _6: (x0,x1,x2) => x0.set(x1,x2),
      _7: (x0,x1) => x0.transferFromImageBitmap(x1),
      _8: x0 => x0.arrayBuffer(),
      _9: (x0,x1,x2) => x0.slice(x1,x2),
      _10: (x0,x1) => x0.decode(x1),
      _11: (x0,x1) => x0.segment(x1),
      _12: () => new TextDecoder(),
      _14: x0 => x0.buffer,
      _15: x0 => x0.wasmMemory,
      _16: () => globalThis.window._flutter_skwasmInstance,
      _17: x0 => x0.rasterStartMilliseconds,
      _18: x0 => x0.rasterEndMilliseconds,
      _19: x0 => x0.imageBitmaps,
      _135: (x0,x1) => x0.appendChild(x1),
      _166: (x0,x1,x2) => x0.addEventListener(x1,x2),
      _167: (x0,x1,x2) => x0.removeEventListener(x1,x2),
      _168: (x0,x1) => new OffscreenCanvas(x0,x1),
      _169: x0 => x0.remove(),
      _170: (x0,x1) => x0.append(x1),
      _172: x0 => x0.unlock(),
      _173: x0 => x0.getReader(),
      _174: (x0,x1) => x0.item(x1),
      _175: x0 => x0.next(),
      _176: x0 => x0.now(),
      _177: (x0,x1) => x0.revokeObjectURL(x1),
      _178: x0 => x0.close(),
      _179: (x0,x1,x2,x3,x4) => ({type: x0,data: x1,premultiplyAlpha: x2,colorSpaceConversion: x3,preferAnimation: x4}),
      _180: x0 => new window.ImageDecoder(x0),
      _181: (x0,x1) => ({frameIndex: x0,completeFramesOnly: x1}),
      _182: (x0,x1) => x0.decode(x1),
      _183: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._183(f,arguments.length,x0) }),
      _184: (x0,x1,x2,x3) => x0.addEventListener(x1,x2,x3),
      _186: (x0,x1) => x0.getModifierState(x1),
      _187: x0 => x0.preventDefault(),
      _188: x0 => x0.stopPropagation(),
      _189: (x0,x1) => x0.removeProperty(x1),
      _190: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._190(f,arguments.length,x0) }),
      _191: x0 => new window.FinalizationRegistry(x0),
      _192: (x0,x1,x2,x3) => x0.register(x1,x2,x3),
      _194: (x0,x1) => x0.unregister(x1),
      _195: (x0,x1) => x0.prepend(x1),
      _196: x0 => new Intl.Locale(x0),
      _197: (x0,x1) => x0.observe(x1),
      _198: x0 => x0.disconnect(),
      _199: (x0,x1) => x0.getAttribute(x1),
      _200: (x0,x1) => x0.contains(x1),
      _201: (x0,x1) => x0.querySelector(x1),
      _202: (x0,x1) => x0.matchMedia(x1),
      _203: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._203(f,arguments.length,x0) }),
      _204: (x0,x1,x2) => x0.call(x1,x2),
      _205: x0 => x0.blur(),
      _206: x0 => x0.hasFocus(),
      _207: (x0,x1) => x0.removeAttribute(x1),
      _208: (x0,x1,x2) => x0.insertBefore(x1,x2),
      _209: (x0,x1) => x0.hasAttribute(x1),
      _210: (x0,x1) => x0.getModifierState(x1),
      _211: (x0,x1) => x0.createTextNode(x1),
      _212: x0 => x0.getBoundingClientRect(),
      _213: (x0,x1) => x0.replaceWith(x1),
      _214: (x0,x1) => x0.contains(x1),
      _215: (x0,x1) => x0.closest(x1),
      _216: () => new Array(),
      _653: x0 => new Uint8Array(x0),
      _656: () => globalThis.window.flutterConfiguration,
      _658: x0 => x0.assetBase,
      _663: x0 => x0.canvasKitMaximumSurfaces,
      _664: x0 => x0.debugShowSemanticsNodes,
      _665: x0 => x0.hostElement,
      _666: x0 => x0.multiViewEnabled,
      _667: x0 => x0.nonce,
      _669: x0 => x0.fontFallbackBaseUrl,
      _679: x0 => x0.console,
      _680: x0 => x0.devicePixelRatio,
      _681: x0 => x0.document,
      _682: x0 => x0.history,
      _683: x0 => x0.innerHeight,
      _684: x0 => x0.innerWidth,
      _685: x0 => x0.location,
      _686: x0 => x0.navigator,
      _687: x0 => x0.visualViewport,
      _688: x0 => x0.performance,
      _689: x0 => x0.parent,
      _691: x0 => x0.URL,
      _693: (x0,x1) => x0.getComputedStyle(x1),
      _694: x0 => x0.screen,
      _695: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._695(f,arguments.length,x0) }),
      _696: (x0,x1) => x0.requestAnimationFrame(x1),
      _700: (x0,x1) => x0.warn(x1),
      _702: (x0,x1) => x0.debug(x1),
      _703: x0 => globalThis.parseFloat(x0),
      _704: () => globalThis.window,
      _705: () => globalThis.Intl,
      _706: () => globalThis.Symbol,
      _707: (x0,x1,x2,x3,x4) => globalThis.createImageBitmap(x0,x1,x2,x3,x4),
      _709: x0 => x0.clipboard,
      _710: x0 => x0.maxTouchPoints,
      _711: x0 => x0.vendor,
      _712: x0 => x0.language,
      _713: x0 => x0.platform,
      _714: x0 => x0.userAgent,
      _715: (x0,x1) => x0.vibrate(x1),
      _716: x0 => x0.languages,
      _717: x0 => x0.documentElement,
      _718: (x0,x1) => x0.querySelector(x1),
      _719: (x0,x1) => x0.querySelectorAll(x1),
      _721: (x0,x1) => x0.createElement(x1),
      _724: (x0,x1) => x0.createEvent(x1),
      _725: x0 => x0.activeElement,
      _728: x0 => x0.head,
      _729: x0 => x0.body,
      _731: (x0,x1) => { x0.title = x1 },
      _734: x0 => x0.visibilityState,
      _735: () => globalThis.document,
      _736: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._736(f,arguments.length,x0) }),
      _737: (x0,x1) => x0.dispatchEvent(x1),
      _745: x0 => x0.target,
      _747: x0 => x0.timeStamp,
      _748: x0 => x0.type,
      _750: (x0,x1,x2,x3) => x0.initEvent(x1,x2,x3),
      _756: x0 => x0.baseURI,
      _757: x0 => x0.firstChild,
      _761: x0 => x0.parentElement,
      _763: (x0,x1) => { x0.textContent = x1 },
      _764: x0 => x0.parentNode,
      _765: x0 => x0.nextSibling,
      _766: (x0,x1) => x0.removeChild(x1),
      _767: x0 => x0.isConnected,
      _775: x0 => x0.clientHeight,
      _776: x0 => x0.clientWidth,
      _777: x0 => x0.offsetHeight,
      _778: x0 => x0.offsetWidth,
      _779: x0 => x0.id,
      _780: (x0,x1) => { x0.id = x1 },
      _783: (x0,x1) => { x0.spellcheck = x1 },
      _784: x0 => x0.tagName,
      _785: x0 => x0.style,
      _787: (x0,x1) => x0.querySelectorAll(x1),
      _788: (x0,x1,x2) => x0.setAttribute(x1,x2),
      _789: x0 => x0.tabIndex,
      _790: (x0,x1) => { x0.tabIndex = x1 },
      _791: (x0,x1) => x0.focus(x1),
      _792: x0 => x0.scrollTop,
      _793: (x0,x1) => { x0.scrollTop = x1 },
      _794: (x0,x1) => { x0.scrollLeft = x1 },
      _795: x0 => x0.scrollLeft,
      _796: x0 => x0.classList,
      _797: (x0,x1) => x0.scrollIntoView(x1),
      _800: (x0,x1) => { x0.className = x1 },
      _802: (x0,x1) => x0.getElementsByClassName(x1),
      _803: x0 => x0.click(),
      _804: (x0,x1) => x0.attachShadow(x1),
      _807: x0 => x0.computedStyleMap(),
      _808: (x0,x1) => x0.get(x1),
      _814: (x0,x1) => x0.getPropertyValue(x1),
      _815: (x0,x1,x2,x3) => x0.setProperty(x1,x2,x3),
      _816: x0 => x0.offsetLeft,
      _817: x0 => x0.offsetTop,
      _818: x0 => x0.offsetParent,
      _820: (x0,x1) => { x0.name = x1 },
      _821: x0 => x0.content,
      _822: (x0,x1) => { x0.content = x1 },
      _826: (x0,x1) => { x0.src = x1 },
      _827: x0 => x0.naturalWidth,
      _828: x0 => x0.naturalHeight,
      _832: (x0,x1) => { x0.crossOrigin = x1 },
      _834: (x0,x1) => { x0.decoding = x1 },
      _835: x0 => x0.decode(),
      _840: (x0,x1) => { x0.nonce = x1 },
      _845: (x0,x1) => { x0.width = x1 },
      _847: (x0,x1) => { x0.height = x1 },
      _850: (x0,x1) => x0.getContext(x1),
      _918: x0 => x0.width,
      _919: x0 => x0.height,
      _921: (x0,x1) => x0.fetch(x1),
      _922: x0 => x0.status,
      _924: x0 => x0.body,
      _925: x0 => x0.arrayBuffer(),
      _927: x0 => x0.text(),
      _928: x0 => x0.read(),
      _929: x0 => x0.value,
      _930: x0 => x0.done,
      _937: x0 => x0.name,
      _938: x0 => x0.x,
      _939: x0 => x0.y,
      _942: x0 => x0.top,
      _943: x0 => x0.right,
      _944: x0 => x0.bottom,
      _945: x0 => x0.left,
      _955: x0 => x0.height,
      _956: x0 => x0.width,
      _957: x0 => x0.scale,
      _958: (x0,x1) => { x0.value = x1 },
      _961: (x0,x1) => { x0.placeholder = x1 },
      _963: (x0,x1) => { x0.name = x1 },
      _964: x0 => x0.selectionDirection,
      _965: x0 => x0.selectionStart,
      _966: x0 => x0.selectionEnd,
      _969: x0 => x0.value,
      _971: (x0,x1,x2) => x0.setSelectionRange(x1,x2),
      _972: x0 => x0.readText(),
      _973: (x0,x1) => x0.writeText(x1),
      _975: x0 => x0.altKey,
      _976: x0 => x0.code,
      _977: x0 => x0.ctrlKey,
      _978: x0 => x0.key,
      _979: x0 => x0.keyCode,
      _980: x0 => x0.location,
      _981: x0 => x0.metaKey,
      _982: x0 => x0.repeat,
      _983: x0 => x0.shiftKey,
      _984: x0 => x0.isComposing,
      _986: x0 => x0.state,
      _987: (x0,x1) => x0.go(x1),
      _989: (x0,x1,x2,x3) => x0.pushState(x1,x2,x3),
      _990: (x0,x1,x2,x3) => x0.replaceState(x1,x2,x3),
      _991: x0 => x0.pathname,
      _992: x0 => x0.search,
      _993: x0 => x0.hash,
      _997: x0 => x0.state,
      _1000: (x0,x1) => x0.createObjectURL(x1),
      _1002: x0 => new Blob(x0),
      _1012: x0 => x0.matches,
      _1016: x0 => x0.matches,
      _1020: x0 => x0.relatedTarget,
      _1022: x0 => x0.clientX,
      _1023: x0 => x0.clientY,
      _1024: x0 => x0.offsetX,
      _1025: x0 => x0.offsetY,
      _1028: x0 => x0.button,
      _1029: x0 => x0.buttons,
      _1030: x0 => x0.ctrlKey,
      _1034: x0 => x0.pointerId,
      _1035: x0 => x0.pointerType,
      _1036: x0 => x0.pressure,
      _1037: x0 => x0.tiltX,
      _1038: x0 => x0.tiltY,
      _1039: x0 => x0.getCoalescedEvents(),
      _1042: x0 => x0.deltaX,
      _1043: x0 => x0.deltaY,
      _1044: x0 => x0.wheelDeltaX,
      _1045: x0 => x0.wheelDeltaY,
      _1046: x0 => x0.deltaMode,
      _1053: x0 => x0.changedTouches,
      _1056: x0 => x0.clientX,
      _1057: x0 => x0.clientY,
      _1060: x0 => x0.data,
      _1063: (x0,x1) => { x0.disabled = x1 },
      _1065: (x0,x1) => { x0.type = x1 },
      _1066: (x0,x1) => { x0.max = x1 },
      _1067: (x0,x1) => { x0.min = x1 },
      _1068: x0 => x0.value,
      _1069: (x0,x1) => { x0.value = x1 },
      _1070: x0 => x0.disabled,
      _1071: (x0,x1) => { x0.disabled = x1 },
      _1073: (x0,x1) => { x0.placeholder = x1 },
      _1075: (x0,x1) => { x0.name = x1 },
      _1076: (x0,x1) => { x0.autocomplete = x1 },
      _1078: x0 => x0.selectionDirection,
      _1079: x0 => x0.selectionStart,
      _1081: x0 => x0.selectionEnd,
      _1084: (x0,x1,x2) => x0.setSelectionRange(x1,x2),
      _1085: (x0,x1) => x0.add(x1),
      _1087: (x0,x1) => { x0.noValidate = x1 },
      _1088: (x0,x1) => { x0.method = x1 },
      _1089: (x0,x1) => { x0.action = x1 },
      _1095: (x0,x1) => x0.getContext(x1),
      _1097: x0 => x0.convertToBlob(),
      _1114: x0 => x0.orientation,
      _1115: x0 => x0.width,
      _1116: x0 => x0.height,
      _1117: (x0,x1) => x0.lock(x1),
      _1136: x0 => new ResizeObserver(x0),
      _1139: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1139(f,arguments.length,x0,x1) }),
      _1147: x0 => x0.length,
      _1148: x0 => x0.iterator,
      _1149: x0 => x0.Segmenter,
      _1150: x0 => x0.v8BreakIterator,
      _1151: (x0,x1) => new Intl.Segmenter(x0,x1),
      _1154: x0 => x0.language,
      _1155: x0 => x0.script,
      _1156: x0 => x0.region,
      _1174: x0 => x0.done,
      _1175: x0 => x0.value,
      _1176: x0 => x0.index,
      _1180: (x0,x1) => new Intl.v8BreakIterator(x0,x1),
      _1181: (x0,x1) => x0.adoptText(x1),
      _1182: x0 => x0.first(),
      _1183: x0 => x0.next(),
      _1184: x0 => x0.current(),
      _1186: () => globalThis.window.FinalizationRegistry,
      _1197: x0 => x0.hostElement,
      _1198: x0 => x0.viewConstraints,
      _1199: x0 => x0.initialData,
      _1201: x0 => x0.maxHeight,
      _1202: x0 => x0.maxWidth,
      _1203: x0 => x0.minHeight,
      _1204: x0 => x0.minWidth,
      _1205: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1205(f,arguments.length,x0) }),
      _1206: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1206(f,arguments.length,x0) }),
      _1207: (x0,x1) => ({addView: x0,removeView: x1}),
      _1210: x0 => x0.loader,
      _1211: () => globalThis._flutter,
      _1212: (x0,x1) => x0.didCreateEngineInitializer(x1),
      _1213: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1213(f,arguments.length,x0) }),
      _1214: (module,f) => finalizeWrapper(f, function() { return module.exports._1214(f,arguments.length) }),
      _1215: (x0,x1) => ({initializeEngine: x0,autoStart: x1}),
      _1218: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1218(f,arguments.length,x0) }),
      _1219: x0 => ({runApp: x0}),
      _1221: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1221(f,arguments.length,x0,x1) }),
      _1222: x0 => new Promise(x0),
      _1223: x0 => x0.length,
      _1224: () => globalThis.window.ImageDecoder,
      _1225: x0 => x0.tracks,
      _1227: x0 => x0.completed,
      _1229: x0 => x0.image,
      _1235: x0 => x0.displayWidth,
      _1236: x0 => x0.displayHeight,
      _1237: x0 => x0.duration,
      _1240: x0 => x0.ready,
      _1241: x0 => x0.selectedTrack,
      _1242: x0 => x0.repetitionCount,
      _1243: x0 => x0.frameCount,
      _1285: x0 => x0.requestFullscreen(),
      _1286: x0 => x0.exitFullscreen(),
      _1287: (x0,x1) => x0.append(x1),
      _1288: (x0,x1,x2) => x0.call(x1,x2),
      _1289: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1289(f,arguments.length,x0,x1) }),
      _1290: x0 => new ResizeObserver(x0),
      _1291: (x0,x1) => x0.observe(x1),
      _1292: (x0,x1,x2,x3) => x0.call(x1,x2,x3),
      _1293: x0 => x0.arrayBuffer(),
      _1295: (x0,x1,x2) => x0.toBlob(x1,x2),
      _1296: (x0,x1) => x0.call(x1),
      _1297: (x0,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12,x13,x14,x15,x16,x17,x18,x19,x20) => x0.call(x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12,x13,x14,x15,x16,x17,x18,x19,x20),
      _1298: x0 => x0.call(),
      _1299: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1299(f,arguments.length,x0) }),
      _1300: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1300(f,arguments.length,x0) }),
      _1301: x0 => x0.call(),
      _1302: (module,f) => finalizeWrapper(f, function(x0,x1,x2,x3) { return module.exports._1302(f,arguments.length,x0,x1,x2,x3) }),
      _1303: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1303(f,arguments.length,x0) }),
      _1304: (module,f) => finalizeWrapper(f, function(x0,x1,x2) { return module.exports._1304(f,arguments.length,x0,x1,x2) }),
      _1305: (module,f) => finalizeWrapper(f, function(x0,x1,x2,x3) { return module.exports._1305(f,arguments.length,x0,x1,x2,x3) }),
      _1306: (module,f) => finalizeWrapper(f, function(x0,x1,x2,x3,x4,x5,x6,x7,x8) { return module.exports._1306(f,arguments.length,x0,x1,x2,x3,x4,x5,x6,x7,x8) }),
      _1307: (module,f) => finalizeWrapper(f, function(x0,x1,x2,x3,x4) { return module.exports._1307(f,arguments.length,x0,x1,x2,x3,x4) }),
      _1308: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1308(f,arguments.length,x0,x1) }),
      _1309: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1309(f,arguments.length,x0) }),
      _1310: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1310(f,arguments.length,x0) }),
      _1311: (module,f) => finalizeWrapper(f, function(x0,x1,x2,x3,x4,x5,x6) { return module.exports._1311(f,arguments.length,x0,x1,x2,x3,x4,x5,x6) }),
      _1312: (module,f) => finalizeWrapper(f, function(x0,x1,x2) { return module.exports._1312(f,arguments.length,x0,x1,x2) }),
      _1313: (module,f) => finalizeWrapper(f, function(x0,x1,x2) { return module.exports._1313(f,arguments.length,x0,x1,x2) }),
      _1314: (module,f) => finalizeWrapper(f, function(x0,x1,x2) { return module.exports._1314(f,arguments.length,x0,x1,x2) }),
      _1315: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1315(f,arguments.length,x0) }),
      _1316: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1316(f,arguments.length,x0) }),
      _1317: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1317(f,arguments.length,x0) }),
      _1318: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1318(f,arguments.length,x0) }),
      _1319: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1319(f,arguments.length,x0) }),
      _1320: (x0,x1,x2,x3,x4) => x0.call(x1,x2,x3,x4),
      _1321: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1321(f,arguments.length,x0,x1) }),
      _1322: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1322(f,arguments.length,x0,x1) }),
      _1323: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1323(f,arguments.length,x0,x1) }),
      _1324: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1324(f,arguments.length,x0,x1) }),
      _1325: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1325(f,arguments.length,x0,x1) }),
      _1326: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1326(f,arguments.length,x0,x1) }),
      _1327: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1327(f,arguments.length,x0,x1) }),
      _1328: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1328(f,arguments.length,x0,x1) }),
      _1329: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1329(f,arguments.length,x0,x1) }),
      _1330: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1330(f,arguments.length,x0) }),
      _1331: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1331(f,arguments.length,x0) }),
      _1332: (x0,x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12) => x0.call(x1,x2,x3,x4,x5,x6,x7,x8,x9,x10,x11,x12),
      _1333: (x0,x1,x2,x3,x4) => x0.call(x1,x2,x3,x4),
      _1335: (x0,x1,x2,x3,x4,x5) => x0.call(x1,x2,x3,x4,x5),
      _1336: (x0,x1,x2,x3,x4,x5,x6,x7,x8) => x0.call(x1,x2,x3,x4,x5,x6,x7,x8),
      _1347: (x0,x1,x2,x3,x4,x5,x6) => x0.call(x1,x2,x3,x4,x5,x6),
      _1370: x0 => x0.createRange(),
      _1371: (x0,x1) => x0.selectNode(x1),
      _1372: x0 => x0.getSelection(),
      _1373: x0 => x0.removeAllRanges(),
      _1374: (x0,x1) => x0.addRange(x1),
      _1375: (x0,x1) => x0.createElement(x1),
      _1376: (x0,x1) => x0.append(x1),
      _1377: (x0,x1,x2) => x0.insertRule(x1,x2),
      _1378: (x0,x1) => x0.add(x1),
      _1379: x0 => x0.preventDefault(),
      _1380: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1380(f,arguments.length,x0) }),
      _1381: (x0,x1,x2) => x0.addEventListener(x1,x2),
      _1382: (x0,x1) => x0.getUserMedia(x1),
      _1383: x0 => x0.getSupportedConstraints(),
      _1384: x0 => x0.getVideoTracks(),
      _1385: x0 => x0.getCapabilities(),
      _1386: x0 => x0.getSettings(),
      _1387: (x0,x1,x2) => x0.setProperty(x1,x2),
      _1388: (x0,x1,x2) => x0.setAttribute(x1,x2),
      _1389: x0 => x0.play(),
      _1390: x0 => x0.pause(),
      _1391: x0 => x0.getTracks(),
      _1392: x0 => x0.stop(),
      _1393: (x0,x1,x2) => x0.translate(x1,x2),
      _1394: (x0,x1,x2) => x0.scale(x1,x2),
      _1395: (x0,x1,x2,x3,x4,x5) => x0.drawImage(x1,x2,x3,x4,x5),
      _1396: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1396(f,arguments.length,x0) }),
      _1397: x0 => globalThis.URL.createObjectURL(x0),
      _1398: x0 => ({torch: x0}),
      _1399: (x0,x1) => x0.applyConstraints(x1),
      _1400: x0 => ({zoom: x0}),
      _1401: x0 => ({mimeType: x0}),
      _1402: (x0,x1) => new MediaRecorder(x0,x1),
      _1403: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1403(f,arguments.length,x0) }),
      _1404: (x0,x1,x2) => x0.addEventListener(x1,x2),
      _1405: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1405(f,arguments.length,x0) }),
      _1406: x0 => x0.start(),
      _1407: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1407(f,arguments.length,x0) }),
      _1408: (x0,x1,x2) => x0.removeEventListener(x1,x2),
      _1409: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1409(f,arguments.length,x0) }),
      _1410: x0 => x0.pause(),
      _1411: x0 => x0.resume(),
      _1412: x0 => x0.stop(),
      _1413: x0 => x0.load(),
      _1414: x0 => globalThis.MediaRecorder.isTypeSupported(x0),
      _1415: x0 => ({type: x0}),
      _1416: (x0,x1) => new Blob(x0,x1),
      _1417: x0 => x0.enumerateDevices(),
      _1418: x0 => new Event(x0),
      _1419: x0 => x0.requestFullscreen(),
      _1420: (x0,x1) => x0.lock(x1),
      _1421: x0 => x0.unlock(),
      _1422: () => globalThis.window.navigator.userAgent,
      _1423: (x0,x1) => x0.get(x1),
      _1424: x0 => x0.text(),
      _1428: (x0,x1,x2,x3) => x0.addEventListener(x1,x2,x3),
      _1429: (x0,x1,x2,x3) => x0.removeEventListener(x1,x2,x3),
      _1430: (x0,x1) => x0.createElement(x1),
      _1436: (x0,x1,x2,x3) => x0.open(x1,x2,x3),
      _1437: (x0,x1) => x0.canShare(x1),
      _1438: (x0,x1) => x0.share(x1),
      _1439: x0 => ({url: x0}),
      _1440: (x0,x1,x2) => ({files: x0,title: x1,text: x2}),
      _1441: (x0,x1) => ({files: x0,text: x1}),
      _1442: (x0,x1) => ({files: x0,title: x1}),
      _1443: x0 => ({files: x0}),
      _1444: (x0,x1) => ({title: x0,text: x1}),
      _1445: x0 => ({text: x0}),
      _1446: x0 => x0.click(),
      _1447: x0 => x0.remove(),
      _1448: () => ({}),
      _1449: (x0,x1,x2) => new File(x0,x1,x2),
      _1450: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1450(f,arguments.length,x0) }),
      _1451: (x0,x1,x2) => globalThis.jsConnect(x0,x1,x2),
      _1452: (x0,x1,x2) => globalThis.jsSend(x0,x1,x2),
      _1453: x0 => globalThis.jsDisconnect(x0),
      _1454: x0 => x0.read(),
      _1455: (x0,x1) => x0.getType(x1),
      _1456: x0 => new ClipboardItem(x0),
      _1457: (x0,x1) => x0.write(x1),
      _1458: x0 => x0.readText(),
      _1460: () => new FileReader(),
      _1466: x0 => ({audio: x0}),
      _1467: x0 => x0.getAudioTracks(),
      _1468: (x0,x1) => x0.removeTrack(x1),
      _1469: x0 => x0.close(),
      _1470: (x0,x1) => x0.warn(x1),
      _1471: x0 => ({sampleRate: x0}),
      _1472: x0 => new AudioContext(x0),
      _1473: () => new AudioContext(),
      _1474: x0 => x0.suspend(),
      _1475: x0 => x0.resume(),
      _1476: (x0,x1) => x0.connect(x1),
      _1477: (x0,x1) => x0.createMediaStreamSource(x1),
      _1478: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1478(f,arguments.length,x0) }),
      _1479: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1479(f,arguments.length,x0) }),
      _1480: (x0,x1) => x0.addModule(x1),
      _1481: x0 => ({parameterData: x0}),
      _1482: (x0,x1,x2) => new AudioWorkletNode(x0,x1,x2),
      _1483: x0 => ({name: x0}),
      _1484: (x0,x1) => x0.query(x1),
      _1485: x0 => globalThis.URL.revokeObjectURL(x0),
      _1488: x0 => x0.disconnect(),
      _1489: (x0,x1,x2) => ({mimeType: x0,audioBitsPerSecond: x1,bitsPerSecond: x2}),
      _1490: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1490(f,arguments.length,x0) }),
      _1491: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1491(f,arguments.length,x0) }),
      _1492: (x0,x1) => x0.start(x1),
      _1493: x0 => x0.createAnalyser(),
      _1494: (x0,x1) => x0.getFloatTimeDomainData(x1),
      _1495: x0 => x0.decode(),
      _1496: (x0,x1,x2,x3) => x0.open(x1,x2,x3),
      _1497: (x0,x1,x2) => x0.setRequestHeader(x1,x2),
      _1498: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1498(f,arguments.length,x0) }),
      _1499: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1499(f,arguments.length,x0) }),
      _1500: x0 => x0.send(),
      _1501: () => new XMLHttpRequest(),
      _1502: (x0,x1) => ({video: x0,audio: x1}),
      _1503: (x0,x1) => x0.createMediaElementSource(x1),
      _1504: x0 => x0.createGain(),
      _1505: x0 => x0.createStereoPanner(),
      _1506: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1506(f,arguments.length,x0) }),
      _1507: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1507(f,arguments.length,x0) }),
      _1508: (x0,x1,x2) => ({enableHighAccuracy: x0,timeout: x1,maximumAge: x2}),
      _1509: (x0,x1,x2,x3) => x0.getCurrentPosition(x1,x2,x3),
      _1510: (x0,x1) => x0.clearWatch(x1),
      _1511: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1511(f,arguments.length,x0) }),
      _1512: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1512(f,arguments.length,x0) }),
      _1513: (x0,x1,x2,x3) => x0.watchPosition(x1,x2,x3),
      _1514: (x0,x1) => x0.getItem(x1),
      _1515: (x0,x1) => x0.removeItem(x1),
      _1516: (x0,x1,x2) => x0.setItem(x1,x2),
      _1517: x0 => ({frequency: x0}),
      _1518: x0 => new Accelerometer(x0),
      _1519: x0 => x0.start(),
      _1520: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1520(f,arguments.length,x0) }),
      _1521: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1521(f,arguments.length,x0) }),
      _1522: x0 => new Gyroscope(x0),
      _1523: x0 => x0.start(),
      _1524: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1524(f,arguments.length,x0) }),
      _1525: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1525(f,arguments.length,x0) }),
      _1526: x0 => new LinearAccelerationSensor(x0),
      _1527: x0 => x0.start(),
      _1528: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1528(f,arguments.length,x0) }),
      _1529: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1529(f,arguments.length,x0) }),
      _1530: x0 => new Magnetometer(x0),
      _1531: x0 => x0.start(),
      _1532: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1532(f,arguments.length,x0) }),
      _1533: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1533(f,arguments.length,x0) }),
      _1534: x0 => ({name: x0}),
      _1535: x0 => ({video: x0}),
      _1536: () => globalThis.Notification.requestPermission(),
      _1537: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1537(f,arguments.length,x0) }),
      _1538: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1538(f,arguments.length,x0) }),
      _1539: (x0,x1,x2) => x0.getCurrentPosition(x1,x2),
      _1542: (x0,x1) => x0.querySelector(x1),
      _1543: (x0,x1) => x0.item(x1),
      _1544: (x0,x1) => x0.readAsDataURL(x1),
      _1545: (x0,x1) => x0.readAsArrayBuffer(x1),
      _1546: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1546(f,arguments.length,x0) }),
      _1547: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1547(f,arguments.length,x0) }),
      _1548: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1548(f,arguments.length,x0) }),
      _1549: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1549(f,arguments.length,x0) }),
      _1550: (x0,x1) => x0.removeChild(x1),
      _1551: x0 => new Blob(x0),
      _1552: (x0,x1,x2) => x0.slice(x1,x2),
      _1553: x0 => x0.deviceMemory,
      _1554: x0 => x0.getBattery(),
      _1555: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1555(f,arguments.length,x0) }),
      _1556: (x0,x1) => x0.key(x1),
      _1557: (x0,x1,x2,x3,x4,x5,x6,x7) => x0.unwrapKey(x1,x2,x3,x4,x5,x6,x7),
      _1558: (x0,x1,x2,x3,x4,x5) => x0.importKey(x1,x2,x3,x4,x5),
      _1559: (x0,x1,x2,x3) => x0.generateKey(x1,x2,x3),
      _1560: (x0,x1,x2,x3,x4) => x0.wrapKey(x1,x2,x3,x4),
      _1561: (x0,x1,x2) => x0.exportKey(x1,x2),
      _1562: (x0,x1) => x0.getRandomValues(x1),
      _1563: (x0,x1,x2,x3) => x0.encrypt(x1,x2,x3),
      _1564: (x0,x1,x2,x3) => x0.decrypt(x1,x2,x3),
      _1565: (x0,x1) => x0.appendChild(x1),
      _1566: (x0,x1) => x0.querySelector(x1),
      _1568: (x0,x1) => x0.matchMedia(x1),
      _1570: x0 => x0.pyodide,
      _1571: x0 => x0.multiView,
      _1573: x0 => x0.webSocketEndpoint,
      _1574: x0 => x0.routeUrlStrategy,
      _1579: x0 => x0.assetsDir,
      _1580: () => globalThis.flet,
      _1581: Date.now,
      _1583: s => new Date(s * 1000).getTimezoneOffset() * 60,
      _1584: s => {
        if (!/^\s*[+-]?(?:Infinity|NaN|(?:\.\d+|\d+(?:\.\d*)?)(?:[eE][+-]?\d+)?)\s*$/.test(s)) {
          return NaN;
        }
        return parseFloat(s);
      },
      _1585: () => typeof dartUseDateNowForTicks !== "undefined",
      _1586: () => 1000 * performance.now(),
      _1587: () => Date.now(),
      _1588: () => {
        // On browsers return `globalThis.location.href`
        if (globalThis.location != null) {
          return globalThis.location.href;
        }
        return null;
      },
      _1589: () => {
        return typeof process != "undefined" &&
               Object.prototype.toString.call(process) == "[object process]" &&
               process.platform == "win32"
      },
      _1590: () => new WeakMap(),
      _1591: (map, o) => map.get(o),
      _1592: (map, o, v) => map.set(o, v),
      _1593: x0 => new WeakRef(x0),
      _1594: x0 => x0.deref(),
      _1595: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1595(f,arguments.length,x0) }),
      _1596: x0 => new FinalizationRegistry(x0),
      _1597: (x0,x1,x2,x3) => x0.register(x1,x2,x3),
      _1598: (x0,x1,x2) => x0.register(x1,x2),
      _1599: (x0,x1) => x0.unregister(x1),
      _1601: () => globalThis.WeakRef,
      _1602: () => globalThis.FinalizationRegistry,
      _1604: s => JSON.stringify(s),
      _1605: s => printToConsole(s),
      _1606: o => {
        if (o === null || o === undefined) return 0;
        if (typeof(o) === 'string') return 1;
        return 2;
      },
      _1607: (o, p, r) => o.replaceAll(p, () => r),
      _1608: (o, p, r) => o.replace(p, () => r),
      _1609: Function.prototype.call.bind(String.prototype.toLowerCase),
      _1610: s => s.toUpperCase(),
      _1611: s => s.trim(),
      _1612: s => s.trimLeft(),
      _1613: s => s.trimRight(),
      _1614: (string, times) => string.repeat(times),
      _1615: Function.prototype.call.bind(String.prototype.indexOf),
      _1616: (s, p, i) => s.lastIndexOf(p, i),
      _1617: (string, token) => string.split(token),
      _1618: Object.is,
      _1622: (o, t) => typeof o === t,
      _1623: (o, c) => o instanceof c,
      _1624: o => Object.keys(o),
      _1627: (o,s,v) => o[s] = v,
      _1628: (o, a) => o + a,
      _1677: x0 => new Array(x0),
      _1679: x0 => x0.length,
      _1681: (x0,x1) => x0[x1],
      _1682: (x0,x1,x2) => { x0[x1] = x2 },
      _1683: (x0,x1) => x0.push(x1),
      _1685: (x0,x1,x2) => new DataView(x0,x1,x2),
      _1687: x0 => new Int8Array(x0),
      _1688: (x0,x1,x2) => new Uint8Array(x0,x1,x2),
      _1690: x0 => new Uint8ClampedArray(x0),
      _1692: x0 => new Int16Array(x0),
      _1694: x0 => new Uint16Array(x0),
      _1696: x0 => new Int32Array(x0),
      _1698: x0 => new Uint32Array(x0),
      _1700: x0 => new Float32Array(x0),
      _1702: x0 => new Float64Array(x0),
      _1724: () => Symbol("jsBoxedDartObjectProperty"),
      _1725: x0 => x0.random(),
      _1726: (x0,x1) => x0.getRandomValues(x1),
      _1727: () => globalThis.crypto,
      _1728: () => globalThis.Math,
      _1741: (ms, c) =>
      setTimeout(() => dartInstance.exports.$invokeCallback(c),ms),
      _1742: (handle) => clearTimeout(handle),
      _1743: (ms, c) =>
      setInterval(() => dartInstance.exports.$invokeCallback(c), ms),
      _1744: (handle) => clearInterval(handle),
      _1745: (c) =>
      queueMicrotask(() => dartInstance.exports.$invokeCallback(c)),
      _1746: () => Date.now(),
      _1747: () => new Error().stack,
      _1748: (exn) => {
        let stackString = exn.toString();
        let frames = stackString.split('\n');
        let drop = 4;
        if (frames[0].startsWith('Error')) {
            drop += 1;
        }
        return frames.slice(drop).join('\n');
      },
      _1749: (s, m) => {
        try {
          return new RegExp(s, m);
        } catch (e) {
          return String(e);
        }
      },
      _1750: (x0,x1) => x0.exec(x1),
      _1751: (x0,x1) => x0.test(x1),
      _1752: x0 => x0.pop(),
      _1754: o => o === undefined,
      _1756: o => typeof o === 'function' && o[jsWrappedDartFunctionSymbol] === true,
      _1758: o => {
        const proto = Object.getPrototypeOf(o);
        return proto === Object.prototype || proto === null;
      },
      _1759: o => o instanceof RegExp,
      _1760: (l, r) => l === r,
      _1761: o => o,
      _1762: o => {
        if (o === undefined || o === null) return 0;
        if (typeof o === 'number') return 1;
        return 2;
      },
      _1763: o => o,
      _1764: o => {
        if (o === undefined || o === null) return 0;
        if (typeof o === 'boolean') return 1;
        return 2;
      },
      _1765: o => o,
      _1766: b => !!b,
      _1767: o => o.length,
      _1769: (o, i) => o[i],
      _1770: f => f.dartFunction,
      _1771: () => ({}),
      _1772: () => [],
      _1774: () => globalThis,
      _1775: (constructor, args) => {
        const factoryFunction = constructor.bind.apply(
            constructor, [null, ...args]);
        return new factoryFunction();
      },
      _1776: (o, p) => p in o,
      _1777: (o, p) => o[p],
      _1778: (o, p, v) => o[p] = v,
      _1779: (o, m, a) => o[m].apply(o, a),
      _1781: o => String(o),
      _1782: (p, s, f) => p.then(s, (e) => f(e, e === undefined)),
      _1783: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1783(f,arguments.length,x0) }),
      _1784: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1784(f,arguments.length,x0,x1) }),
      _1785: o => {
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
      _1786: o => [o],
      _1787: (o0, o1) => [o0, o1],
      _1788: (o0, o1, o2) => [o0, o1, o2],
      _1789: (o0, o1, o2, o3) => [o0, o1, o2, o3],
      _1790: (exn) => {
        if (exn instanceof Error) {
          return exn.stack;
        } else {
          return null;
        }
      },
      _1791: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmI8ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1792: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmI8ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1793: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmI16ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1794: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmI16ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1795: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmI32ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1796: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmI32ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1797: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmF32ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1798: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmF32ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1799: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const getValue = dartInstance.exports.$wasmF64ArrayGet;
        for (let i = 0; i < length; i++) {
          jsArray[jsArrayOffset + i] = getValue(wasmArray, wasmArrayOffset + i);
        }
      },
      _1800: (jsArray, jsArrayOffset, wasmArray, wasmArrayOffset, length) => {
        const setValue = dartInstance.exports.$wasmF64ArraySet;
        for (let i = 0; i < length; i++) {
          setValue(wasmArray, wasmArrayOffset + i, jsArray[jsArrayOffset + i]);
        }
      },
      _1801: x0 => new ArrayBuffer(x0),
      _1802: s => {
        if (/[[\]{}()*+?.\\^$|]/.test(s)) {
            s = s.replace(/[[\]{}()*+?.\\^$|]/g, '\\$&');
        }
        return s;
      },
      _1803: x0 => x0.input,
      _1804: x0 => x0.index,
      _1805: x0 => x0.groups,
      _1806: x0 => x0.flags,
      _1807: x0 => x0.multiline,
      _1808: x0 => x0.ignoreCase,
      _1809: x0 => x0.unicode,
      _1810: x0 => x0.dotAll,
      _1811: (x0,x1) => { x0.lastIndex = x1 },
      _1812: (o, p) => p in o,
      _1813: (o, p) => o[p],
      _1814: (o, p, v) => o[p] = v,
      _1815: (o, p) => delete o[p],
      _1816: (x0,x1) => x0.end(x1),
      _1818: (x0,x1,x2,x3) => x0.drawImage(x1,x2,x3),
      _1819: (x0,x1) => x0.toDataURL(x1),
      _1820: (x0,x1,x2) => x0.setRequestHeader(x1,x2),
      _1821: (module,f) => finalizeWrapper(f, function(x0,x1) { return module.exports._1821(f,arguments.length,x0,x1) }),
      _1822: x0 => ({xhrSetup: x0}),
      _1823: x0 => new Hls(x0),
      _1824: (x0,x1) => x0.loadSource(x1),
      _1825: (x0,x1) => x0.attachMedia(x1),
      _1826: (x0,x1) => x0.canPlayType(x1),
      _1827: () => globalThis.Hls.isSupported(),
      _1828: () => new XMLHttpRequest(),
      _1829: (x0,x1,x2,x3) => x0.open(x1,x2,x3),
      _1832: x0 => x0.send(),
      _1834: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1834(f,arguments.length,x0) }),
      _1835: (module,f) => finalizeWrapper(f, function(x0) { return module.exports._1835(f,arguments.length,x0) }),
      _1840: (x0,x1) => new WebSocket(x0,x1),
      _1841: (x0,x1) => x0.send(x1),
      _1842: (x0,x1,x2) => x0.close(x1,x2),
      _1844: x0 => x0.close(),
      _1846: (x0,x1) => x0.append(x1),
      _1848: () => new AbortController(),
      _1849: x0 => x0.abort(),
      _1850: (x0,x1,x2,x3,x4,x5) => ({method: x0,headers: x1,body: x2,credentials: x3,redirect: x4,signal: x5}),
      _1851: (x0,x1) => globalThis.fetch(x0,x1),
      _1852: (module,f) => finalizeWrapper(f, function(x0,x1,x2) { return module.exports._1852(f,arguments.length,x0,x1,x2) }),
      _1853: (x0,x1) => x0.forEach(x1),
      _1854: x0 => x0.getReader(),
      _1855: x0 => x0.cancel(),
      _1856: x0 => x0.read(),
      _1858: x0 => x0.zoom,
      _1859: x0 => x0.torch,
      _1860: x0 => x0.zoom,
      _1861: x0 => x0.torch,
      _1863: x0 => x0.facingMode,
      _1865: x0 => x0.max,
      _1867: x0 => x0.min,
      _1872: (x0,x1,x2,x3) => ({method: x0,headers: x1,body: x2,credentials: x3}),
      _1873: (x0,x1,x2) => x0.fetch(x1,x2),
      _1874: o => o instanceof Array,
      _1875: (a, i) => a.splice(i, 1)[0],
      _1876: (a, i, v) => a.splice(i, 0, v),
      _1877: (a, l) => a.length = l,
      _1878: a => a.pop(),
      _1879: (a, i) => a.splice(i, 1),
      _1880: (a, s) => a.join(s),
      _1881: (a, s, e) => a.slice(s, e),
      _1883: (a, b) => a == b ? 0 : (a > b ? 1 : -1),
      _1884: a => a.length,
      _1885: (a, l) => a.length = l,
      _1886: (a, i) => a[i],
      _1887: (a, i, v) => a[i] = v,
      _1889: o => {
        if (o === null || o === undefined) return 0;
        if (o instanceof ArrayBuffer) return 1;
        if (globalThis.SharedArrayBuffer !== undefined &&
            o instanceof SharedArrayBuffer) {
          return 2;
        }
        return 3;
      },
      _1890: (o, offsetInBytes, lengthInBytes) => {
        var dst = new ArrayBuffer(lengthInBytes);
        new Uint8Array(dst).set(new Uint8Array(o, offsetInBytes, lengthInBytes));
        return new DataView(dst);
      },
      _1891: o => {
        if (o === null || o === undefined) return 0;
        if (o instanceof DataView) return 1;
        return 2;
      },
      _1892: o => {
        if (o === null || o === undefined) return 0;
        if (o instanceof Uint8Array) return 1;
        return 2;
      },
      _1893: (o, start, length) => new Uint8Array(o.buffer, o.byteOffset + start, length),
      _1894: o => {
        if (o === null || o === undefined) return 0;
        if (o instanceof Int8Array) return 1;
        return 2;
      },
      _1895: (o, start, length) => new Int8Array(o.buffer, o.byteOffset + start, length),
      _1896: o => o instanceof Uint8ClampedArray,
      _1897: (o, start, length) => new Uint8ClampedArray(o.buffer, o.byteOffset + start, length),
      _1898: o => o instanceof Uint16Array,
      _1899: (o, start, length) => new Uint16Array(o.buffer, o.byteOffset + start, length),
      _1900: o => o instanceof Int16Array,
      _1901: (o, start, length) => new Int16Array(o.buffer, o.byteOffset + start, length),
      _1902: o => {
        if (o === null || o === undefined) return 0;
        if (o instanceof Uint32Array) return 1;
        return 2;
      },
      _1903: (o, start, length) => new Uint32Array(o.buffer, o.byteOffset + start, length),
      _1904: o => {
        if (o === null || o === undefined) return 0;
        if (o instanceof Int32Array) return 1;
        return 2;
      },
      _1905: (o, start, length) => new Int32Array(o.buffer, o.byteOffset + start, length),
      _1907: (o, start, length) => new BigInt64Array(o.buffer, o.byteOffset + start, length),
      _1908: o => {
        if (o === null || o === undefined) return 0;
        if (o instanceof Float32Array) return 1;
        return 2;
      },
      _1909: (o, start, length) => new Float32Array(o.buffer, o.byteOffset + start, length),
      _1910: o => {
        if (o === null || o === undefined) return 0;
        if (o instanceof Float64Array) return 1;
        return 2;
      },
      _1911: (o, start, length) => new Float64Array(o.buffer, o.byteOffset + start, length),
      _1912: (a, i) => a.push(i),
      _1913: (t, s) => t.set(s),
      _1914: l => new DataView(new ArrayBuffer(l)),
      _1915: (o) => new DataView(o.buffer, o.byteOffset, o.byteLength),
      _1916: o => o.byteLength,
      _1917: o => o.buffer,
      _1918: o => o.byteOffset,
      _1919: Function.prototype.call.bind(Object.getOwnPropertyDescriptor(DataView.prototype, 'byteLength').get),
      _1920: (b, o) => new DataView(b, o),
      _1921: (b, o, l) => new DataView(b, o, l),
      _1922: Function.prototype.call.bind(DataView.prototype.getUint8),
      _1923: Function.prototype.call.bind(DataView.prototype.setUint8),
      _1924: Function.prototype.call.bind(DataView.prototype.getInt8),
      _1925: Function.prototype.call.bind(DataView.prototype.setInt8),
      _1926: Function.prototype.call.bind(DataView.prototype.getUint16),
      _1927: Function.prototype.call.bind(DataView.prototype.setUint16),
      _1928: Function.prototype.call.bind(DataView.prototype.getInt16),
      _1929: Function.prototype.call.bind(DataView.prototype.setInt16),
      _1930: Function.prototype.call.bind(DataView.prototype.getUint32),
      _1931: Function.prototype.call.bind(DataView.prototype.setUint32),
      _1932: Function.prototype.call.bind(DataView.prototype.getInt32),
      _1933: Function.prototype.call.bind(DataView.prototype.setInt32),
      _1934: Function.prototype.call.bind(DataView.prototype.getBigUint64),
      _1936: Function.prototype.call.bind(DataView.prototype.getBigInt64),
      _1937: Function.prototype.call.bind(DataView.prototype.setBigInt64),
      _1938: Function.prototype.call.bind(DataView.prototype.getFloat32),
      _1939: Function.prototype.call.bind(DataView.prototype.setFloat32),
      _1940: Function.prototype.call.bind(DataView.prototype.getFloat64),
      _1941: Function.prototype.call.bind(DataView.prototype.setFloat64),
      _1942: Function.prototype.call.bind(Number.prototype.toString),
      _1943: Function.prototype.call.bind(BigInt.prototype.toString),
      _1944: Function.prototype.call.bind(Number.prototype.toString),
      _1945: (d, digits) => d.toFixed(digits),
      _1951: (x0,x1) => x0.getContext(x1),
      _2004: (x0,x1) => { x0.responseType = x1 },
      _2005: x0 => x0.response,
      _2065: (x0,x1) => { x0.draggable = x1 },
      _2081: x0 => x0.style,
      _2438: (x0,x1) => { x0.target = x1 },
      _2440: (x0,x1) => { x0.download = x1 },
      _2465: (x0,x1) => { x0.href = x1 },
      _2558: (x0,x1) => { x0.src = x1 },
      _2653: x0 => x0.videoWidth,
      _2654: x0 => x0.videoHeight,
      _2666: (x0,x1) => { x0.kind = x1 },
      _2668: (x0,x1) => { x0.src = x1 },
      _2670: (x0,x1) => { x0.srclang = x1 },
      _2672: (x0,x1) => { x0.label = x1 },
      _2683: x0 => x0.error,
      _2685: (x0,x1) => { x0.src = x1 },
      _2686: x0 => x0.srcObject,
      _2687: (x0,x1) => { x0.srcObject = x1 },
      _2690: (x0,x1) => { x0.crossOrigin = x1 },
      _2693: (x0,x1) => { x0.preload = x1 },
      _2694: x0 => x0.buffered,
      _2697: x0 => x0.currentTime,
      _2698: (x0,x1) => { x0.currentTime = x1 },
      _2699: x0 => x0.duration,
      _2700: x0 => x0.paused,
      _2703: x0 => x0.playbackRate,
      _2704: (x0,x1) => { x0.playbackRate = x1 },
      _2711: (x0,x1) => { x0.autoplay = x1 },
      _2713: (x0,x1) => { x0.loop = x1 },
      _2715: (x0,x1) => { x0.controls = x1 },
      _2716: x0 => x0.volume,
      _2717: (x0,x1) => { x0.volume = x1 },
      _2718: x0 => x0.muted,
      _2719: (x0,x1) => { x0.muted = x1 },
      _2724: x0 => x0.textTracks,
      _2734: x0 => x0.code,
      _2735: x0 => x0.message,
      _2769: (x0,x1) => x0[x1],
      _2771: x0 => x0.length,
      _2786: (x0,x1) => { x0.mode = x1 },
      _2788: x0 => x0.activeCues,
      _2809: x0 => x0.length,
      _3005: (x0,x1) => { x0.accept = x1 },
      _3019: x0 => x0.files,
      _3045: (x0,x1) => { x0.multiple = x1 },
      _3063: (x0,x1) => { x0.type = x1 },
      _3312: (x0,x1) => { x0.src = x1 },
      _3314: (x0,x1) => { x0.type = x1 },
      _3318: (x0,x1) => { x0.async = x1 },
      _3320: (x0,x1) => { x0.defer = x1 },
      _3332: (x0,x1) => { x0.charset = x1 },
      _3357: x0 => x0.width,
      _3358: (x0,x1) => { x0.width = x1 },
      _3359: x0 => x0.height,
      _3360: (x0,x1) => { x0.height = x1 },
      _3779: () => globalThis.window,
      _3816: x0 => x0.document,
      _3838: x0 => x0.navigator,
      _3842: x0 => x0.screen,
      _3845: x0 => x0.innerHeight,
      _3849: x0 => x0.screenLeft,
      _3853: x0 => x0.outerHeight,
      _3854: x0 => x0.devicePixelRatio,
      _4093: x0 => x0.isSecureContext,
      _4096: x0 => x0.crypto,
      _4101: x0 => x0.sessionStorage,
      _4102: x0 => x0.localStorage,
      _4161: x0 => x0.message,
      _4203: x0 => x0.clipboard,
      _4205: x0 => x0.geolocation,
      _4208: x0 => x0.mediaDevices,
      _4210: x0 => x0.permissions,
      _4211: x0 => x0.maxTouchPoints,
      _4218: x0 => x0.appCodeName,
      _4219: x0 => x0.appName,
      _4220: x0 => x0.appVersion,
      _4221: x0 => x0.platform,
      _4222: x0 => x0.product,
      _4223: x0 => x0.productSub,
      _4224: x0 => x0.userAgent,
      _4225: x0 => x0.vendor,
      _4226: x0 => x0.vendorSub,
      _4228: x0 => x0.language,
      _4229: x0 => x0.languages,
      _4230: x0 => x0.onLine,
      _4235: x0 => x0.hardwareConcurrency,
      _4275: x0 => x0.data,
      _4312: (x0,x1) => { x0.onmessage = x1 },
      _4432: x0 => x0.length,
      _4649: x0 => x0.readyState,
      _4658: x0 => x0.protocol,
      _4662: (x0,x1) => { x0.binaryType = x1 },
      _4665: x0 => x0.code,
      _4666: x0 => x0.reason,
      _5815: x0 => x0.destination,
      _5816: x0 => x0.sampleRate,
      _5819: x0 => x0.state,
      _5820: x0 => x0.audioWorklet,
      _5907: (x0,x1) => { x0.value = x1 },
      _5921: x0 => x0.fftSize,
      _5922: (x0,x1) => { x0.fftSize = x1 },
      _5929: (x0,x1) => { x0.smoothingTimeConstant = x1 },
      _6055: x0 => x0.gain,
      _6183: x0 => x0.port,
      _6322: x0 => x0.type,
      _6363: x0 => x0.signal,
      _6419: x0 => x0.isConnected,
      _6424: x0 => x0.firstChild,
      _6435: () => globalThis.document,
      _6494: x0 => x0.documentElement,
      _6515: x0 => x0.body,
      _6517: x0 => x0.head,
      _6844: x0 => x0.id,
      _6845: (x0,x1) => { x0.id = x1 },
      _6869: (x0,x1) => { x0.innerHTML = x1 },
      _6872: x0 => x0.children,
      _8190: x0 => x0.value,
      _8192: x0 => x0.done,
      _8371: x0 => x0.size,
      _8372: x0 => x0.type,
      _8375: (x0,x1) => { x0.type = x1 },
      _8378: x0 => x0.name,
      _8384: x0 => x0.length,
      _8389: x0 => x0.result,
      _8758: x0 => x0.mimeType,
      _8759: x0 => x0.state,
      _8763: (x0,x1) => { x0.onstop = x1 },
      _8765: (x0,x1) => { x0.ondataavailable = x1 },
      _8778: (x0,x1) => { x0.audioBitsPerSecond = x1 },
      _8780: (x0,x1) => { x0.videoBitsPerSecond = x1 },
      _8790: x0 => x0.data,
      _8879: x0 => x0.url,
      _8881: x0 => x0.status,
      _8883: x0 => x0.statusText,
      _8884: x0 => x0.headers,
      _8885: x0 => x0.body,
      _8960: x0 => x0.types,
      _9147: x0 => x0.type,
      _9162: x0 => x0.matches,
      _9175: x0 => x0.width,
      _9176: x0 => x0.height,
      _9179: x0 => x0.orientation,
      _9266: x0 => x0.state,
      _9665: x0 => x0.active,
      _9697: x0 => x0.facingMode,
      _9911: x0 => x0.width,
      _9913: x0 => x0.height,
      _9923: x0 => x0.sampleRate,
      _9935: x0 => x0.channelCount,
      _9996: x0 => x0.deviceId,
      _9997: x0 => x0.kind,
      _9998: x0 => x0.label,
      _10573: x0 => x0.coords,
      _10574: x0 => x0.timestamp,
      _10576: x0 => x0.accuracy,
      _10577: x0 => x0.latitude,
      _10578: x0 => x0.longitude,
      _10579: x0 => x0.altitude,
      _10580: x0 => x0.altitudeAccuracy,
      _10581: x0 => x0.heading,
      _10582: x0 => x0.speed,
      _10583: x0 => x0.code,
      _10584: x0 => x0.message,
      _10992: (x0,x1) => { x0.border = x1 },
      _11270: (x0,x1) => { x0.display = x1 },
      _11434: (x0,x1) => { x0.height = x1 },
      _11628: (x0,x1) => { x0.objectFit = x1 },
      _11758: (x0,x1) => { x0.pointerEvents = x1 },
      _12056: (x0,x1) => { x0.transform = x1 },
      _12060: (x0,x1) => { x0.transformOrigin = x1 },
      _12124: (x0,x1) => { x0.width = x1 },
      _12415: x0 => x0.charging,
      _12418: x0 => x0.level,
      _12420: (x0,x1) => { x0.onchargingchange = x1 },
      _12492: x0 => x0.name,
      _12493: x0 => x0.message,
      _12496: x0 => x0.subtle,
      _13202: () => globalThis.console,
      _13226: () => globalThis.document,
      _13227: () => globalThis.window,
      _13228: () => globalThis.console,
      _13233: (x0,x1) => { x0.height = x1 },
      _13235: (x0,x1) => { x0.width = x1 },
      _13237: (x0,x1) => { x0.pointerEvents = x1 },
      _13240: x0 => x0.head,
      _13241: x0 => x0.classList,
      _13245: (x0,x1) => { x0.innerText = x1 },
      _13246: x0 => x0.style,
      _13248: x0 => x0.sheet,
      _13249: x0 => x0.src,
      _13250: (x0,x1) => { x0.src = x1 },
      _13251: x0 => x0.naturalWidth,
      _13252: x0 => x0.naturalHeight,
      _13259: x0 => x0.offsetX,
      _13260: x0 => x0.offsetY,
      _13261: x0 => x0.button,
      _13267: (x0,x1) => x0.error(x1),
      _13272: x0 => x0.status,
      _13273: (x0,x1) => { x0.responseType = x1 },
      _13275: x0 => x0.response,
      _13276: x0 => x0.x,
      _13277: x0 => x0.y,
      _13278: x0 => x0.z,
      _13279: (x0,x1) => { x0.onreading = x1 },
      _13280: (x0,x1) => { x0.onerror = x1 },
      _13281: x0 => x0.x,
      _13282: x0 => x0.y,
      _13283: x0 => x0.z,
      _13284: (x0,x1) => { x0.onreading = x1 },
      _13285: (x0,x1) => { x0.onerror = x1 },
      _13286: x0 => x0.x,
      _13287: x0 => x0.y,
      _13288: x0 => x0.z,
      _13289: (x0,x1) => { x0.onreading = x1 },
      _13290: (x0,x1) => { x0.onerror = x1 },
      _13291: x0 => x0.x,
      _13292: x0 => x0.y,
      _13293: x0 => x0.z,
      _13294: (x0,x1) => { x0.onreading = x1 },
      _13295: (x0,x1) => { x0.onerror = x1 },
      _13296: x0 => x0.error,
      _13297: x0 => x0.name,
      _13298: x0 => x0.message,
      _13303: x0 => globalThis.Wakelock.toggle(x0),
      _13304: () => globalThis.Wakelock.enabled(),

    };

    const baseImports = {
      dart2wasm: dart2wasm,
      Math: Math,
      Date: Date,
      Object: Object,
      Array: Array,
      Reflect: Reflect,
      WebAssembly: {
        JSTag: WebAssembly.JSTag,
      },
      s: [
        "([ \r\n\t]+)|([!-\\[\\]-‧‪-퟿豈-￿][̀-ͯ]*|[\ud800-\udbff][\udc00-\udfff][̀-ͯ]*|\\\\verb\\*([^]).*?\\3|\\\\verb([^*a-zA-Z]).*?\\4|\\\\operatorname\\*|\\\\[a-zA-Z@]+[ \r\n\t]*|\\\\[^\ud800-\udfff])",
      ],
      "": new Proxy({}, { get(_, prop) { return prop; } }),

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
    dartInstance.exports.$setThisModule(dartInstance);

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
