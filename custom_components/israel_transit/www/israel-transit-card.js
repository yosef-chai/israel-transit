/* Israel Transit card - https://github.com/yosef-chai/israel-transit */
var C5=Object.defineProperty;var H5=(M,C,H)=>C in M?C5(M,C,{enumerable:!0,configurable:!0,writable:!0,value:H}):M[C]=H;var l=(M,C,H)=>H5(M,typeof C!="symbol"?C+"":C,H);var p1=globalThis,m1=p1.ShadowRoot&&(p1.ShadyCSS===void 0||p1.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,O1=Symbol(),U1=new WeakMap,C1=class{constructor(C,H,V){if(this._$cssResult$=!0,V!==O1)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=C,this.t=H}get styleSheet(){let C=this.o,H=this.t;if(m1&&C===void 0){let V=H!==void 0&&H.length===1;V&&(C=U1.get(H)),C===void 0&&((this.o=C=new CSSStyleSheet).replaceSync(this.cssText),V&&U1.set(H,C))}return C}toString(){return this.cssText}},n1=M=>new C1(typeof M=="string"?M:M+"",void 0,O1),O=(M,...C)=>{let H=M.length===1?M[0]:C.reduce((V,L,r)=>V+(e=>{if(e._$cssResult$===!0)return e.cssText;if(typeof e=="number")return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(L)+M[r+1],M[0]);return new C1(H,M,O1)},G1=(M,C)=>{if(m1)M.adoptedStyleSheets=C.map(H=>H instanceof CSSStyleSheet?H:H.styleSheet);else for(let H of C){let V=document.createElement("style"),L=p1.litNonce;L!==void 0&&V.setAttribute("nonce",L),V.textContent=H.cssText,M.appendChild(V)}},f1=m1?M=>M:M=>M instanceof CSSStyleSheet?(C=>{let H="";for(let V of C.cssRules)H+=V.cssText;return n1(H)})(M):M;var{is:V5,defineProperty:L5,getOwnPropertyDescriptor:M5,getOwnPropertyNames:r5,getOwnPropertySymbols:e5,getPrototypeOf:t5}=Object,l1=globalThis,Q1=l1.trustedTypes,i5=Q1?Q1.emptyScript:"",o5=l1.reactiveElementPolyfillSupport,H1=(M,C)=>M,g1={toAttribute(M,C){switch(C){case Boolean:M=M?i5:null;break;case Object:case Array:M=M==null?M:JSON.stringify(M)}return M},fromAttribute(M,C){let H=M;switch(C){case Boolean:H=M!==null;break;case Number:H=M===null?null:Number(M);break;case Object:case Array:try{H=JSON.parse(M)}catch{H=null}}return H}},q1=(M,C)=>!V5(M,C),K1={attribute:!0,type:String,converter:g1,reflect:!1,useDefault:!1,hasChanged:q1};Symbol.metadata??=Symbol("metadata"),l1.litPropertyMetadata??=new WeakMap;var g=class extends HTMLElement{static addInitializer(C){this._$Ei(),(this.l??=[]).push(C)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(C,H=K1){if(H.state&&(H.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(C)&&((H=Object.create(H)).wrapped=!0),this.elementProperties.set(C,H),!H.noAccessor){let V=Symbol(),L=this.getPropertyDescriptor(C,V,H);L!==void 0&&L5(this.prototype,C,L)}}static getPropertyDescriptor(C,H,V){let{get:L,set:r}=M5(this.prototype,C)??{get(){return this[H]},set(e){this[H]=e}};return{get:L,set(e){let t=L?.call(this);r?.call(this,e),this.requestUpdate(C,t,V)},configurable:!0,enumerable:!0}}static getPropertyOptions(C){return this.elementProperties.get(C)??K1}static _$Ei(){if(this.hasOwnProperty(H1("elementProperties")))return;let C=t5(this);C.finalize(),C.l!==void 0&&(this.l=[...C.l]),this.elementProperties=new Map(C.elementProperties)}static finalize(){if(this.hasOwnProperty(H1("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(H1("properties"))){let H=this.properties,V=[...r5(H),...e5(H)];for(let L of V)this.createProperty(L,H[L])}let C=this[Symbol.metadata];if(C!==null){let H=litPropertyMetadata.get(C);if(H!==void 0)for(let[V,L]of H)this.elementProperties.set(V,L)}this._$Eh=new Map;for(let[H,V]of this.elementProperties){let L=this._$Eu(H,V);L!==void 0&&this._$Eh.set(L,H)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(C){let H=[];if(Array.isArray(C)){let V=new Set(C.flat(1/0).reverse());for(let L of V)H.unshift(f1(L))}else C!==void 0&&H.push(f1(C));return H}static _$Eu(C,H){let V=H.attribute;return V===!1?void 0:typeof V=="string"?V:typeof C=="string"?C.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(C=>this.enableUpdating=C),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(C=>C(this))}addController(C){(this._$EO??=new Set).add(C),this.renderRoot!==void 0&&this.isConnected&&C.hostConnected?.()}removeController(C){this._$EO?.delete(C)}_$E_(){let C=new Map,H=this.constructor.elementProperties;for(let V of H.keys())this.hasOwnProperty(V)&&(C.set(V,this[V]),delete this[V]);C.size>0&&(this._$Ep=C)}createRenderRoot(){let C=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return G1(C,this.constructor.elementStyles),C}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(C=>C.hostConnected?.())}enableUpdating(C){}disconnectedCallback(){this._$EO?.forEach(C=>C.hostDisconnected?.())}attributeChangedCallback(C,H,V){this._$AK(C,V)}_$ET(C,H){let V=this.constructor.elementProperties.get(C),L=this.constructor._$Eu(C,V);if(L!==void 0&&V.reflect===!0){let r=(V.converter?.toAttribute!==void 0?V.converter:g1).toAttribute(H,V.type);this._$Em=C,r==null?this.removeAttribute(L):this.setAttribute(L,r),this._$Em=null}}_$AK(C,H){let V=this.constructor,L=V._$Eh.get(C);if(L!==void 0&&this._$Em!==L){let r=V.getPropertyOptions(L),e=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:g1;this._$Em=L;let t=e.fromAttribute(H,r.type);this[L]=t??this._$Ej?.get(L)??t,this._$Em=null}}requestUpdate(C,H,V,L=!1,r){if(C!==void 0){let e=this.constructor;if(L===!1&&(r=this[C]),V??=e.getPropertyOptions(C),!((V.hasChanged??q1)(r,H)||V.useDefault&&V.reflect&&r===this._$Ej?.get(C)&&!this.hasAttribute(e._$Eu(C,V))))return;this.C(C,H,V)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(C,H,{useDefault:V,reflect:L,wrapped:r},e){V&&!(this._$Ej??=new Map).has(C)&&(this._$Ej.set(C,e??H??this[C]),r!==!0||e!==void 0)||(this._$AL.has(C)||(this.hasUpdated||V||(H=void 0),this._$AL.set(C,H)),L===!0&&this._$Em!==C&&(this._$Eq??=new Set).add(C))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(H){Promise.reject(H)}let C=this.scheduleUpdate();return C!=null&&await C,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[L,r]of this._$Ep)this[L]=r;this._$Ep=void 0}let V=this.constructor.elementProperties;if(V.size>0)for(let[L,r]of V){let{wrapped:e}=r,t=this[L];e!==!0||this._$AL.has(L)||t===void 0||this.C(L,void 0,r,t)}}let C=!1,H=this._$AL;try{C=this.shouldUpdate(H),C?(this.willUpdate(H),this._$EO?.forEach(V=>V.hostUpdate?.()),this.update(H)):this._$EM()}catch(V){throw C=!1,this._$EM(),V}C&&this._$AE(H)}willUpdate(C){}_$AE(C){this._$EO?.forEach(H=>H.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(C)),this.updated(C)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(C){return!0}update(C){this._$Eq&&=this._$Eq.forEach(H=>this._$ET(H,this[H])),this._$EM()}updated(C){}firstUpdated(C){}};g.elementStyles=[],g.shadowRootOptions={mode:"open"},g[H1("elementProperties")]=new Map,g[H1("finalized")]=new Map,o5?.({ReactiveElement:g}),(l1.reactiveElementVersions??=[]).push("2.1.2");var T1=globalThis,j1=M=>M,v1=T1.trustedTypes,X1=v1?v1.createPolicy("lit-html",{createHTML:M=>M}):void 0,L2="$lit$",w=`lit$${Math.random().toFixed(9).slice(2)}$`,M2="?"+w,a5=`<${M2}>`,F=document,L1=()=>F.createComment(""),M1=M=>M===null||typeof M!="object"&&typeof M!="function",_1=Array.isArray,A5=M=>_1(M)||typeof M?.[Symbol.iterator]=="function",k1=`[ 	
\f\r]`,V1=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Y1=/-->/g,J1=/>/g,_=RegExp(`>|${k1}(?:([^\\s"'>=/]+)(${k1}*=${k1}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),C2=/'/g,H2=/"/g,r2=/^(?:script|style|textarea|title)$/i,R1=M=>(C,...H)=>({_$litType$:M,strings:C,values:H}),o=R1(1),Y5=R1(2),J5=R1(3),D=Symbol.for("lit-noChange"),a=Symbol.for("lit-nothing"),V2=new WeakMap,R=F.createTreeWalker(F,129);function e2(M,C){if(!_1(M)||!M.hasOwnProperty("raw"))throw Error("invalid template strings array");return X1!==void 0?X1.createHTML(C):C}var d5=(M,C)=>{let H=M.length-1,V=[],L,r=C===2?"<svg>":C===3?"<math>":"",e=V1;for(let t=0;t<H;t++){let i=M[t],A,d,p=-1,v=0;for(;v<i.length&&(e.lastIndex=v,d=e.exec(i),d!==null);)v=e.lastIndex,e===V1?d[1]==="!--"?e=Y1:d[1]!==void 0?e=J1:d[2]!==void 0?(r2.test(d[2])&&(L=RegExp("</"+d[2],"g")),e=_):d[3]!==void 0&&(e=_):e===_?d[0]===">"?(e=L??V1,p=-1):d[1]===void 0?p=-2:(p=e.lastIndex-d[2].length,A=d[1],e=d[3]===void 0?_:d[3]==='"'?H2:C2):e===H2||e===C2?e=_:e===Y1||e===J1?e=V1:(e=_,L=void 0);let x=e===_&&M[t+1].startsWith("/>")?" ":"";r+=e===V1?i+a5:p>=0?(V.push(A),i.slice(0,p)+L2+i.slice(p)+w+x):i+w+(p===-2?t:x)}return[e2(M,r+(M[H]||"<?>")+(C===2?"</svg>":C===3?"</math>":"")),V]},r1=class M{constructor({strings:C,_$litType$:H},V){let L;this.parts=[];let r=0,e=0,t=C.length-1,i=this.parts,[A,d]=d5(C,H);if(this.el=M.createElement(A,V),R.currentNode=this.el.content,H===2||H===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(L=R.nextNode())!==null&&i.length<t;){if(L.nodeType===1){if(L.hasAttributes())for(let p of L.getAttributeNames())if(p.endsWith(L2)){let v=d[e++],x=L.getAttribute(p).split(w),u=/([.?@])?(.*)/.exec(v);i.push({type:1,index:r,name:u[2],strings:x,ctor:u[1]==="."?w1:u[1]==="?"?y1:u[1]==="@"?B1:U}),L.removeAttribute(p)}else p.startsWith(w)&&(i.push({type:6,index:r}),L.removeAttribute(p));if(r2.test(L.tagName)){let p=L.textContent.split(w),v=p.length-1;if(v>0){L.textContent=v1?v1.emptyScript:"";for(let x=0;x<v;x++)L.append(p[x],L1()),R.nextNode(),i.push({type:2,index:++r});L.append(p[v],L1())}}}else if(L.nodeType===8)if(L.data===M2)i.push({type:2,index:r});else{let p=-1;for(;(p=L.data.indexOf(w,p+1))!==-1;)i.push({type:7,index:r}),p+=w.length-1}r++}}static createElement(C,H){let V=F.createElement("template");return V.innerHTML=C,V}};function z(M,C,H=M,V){if(C===D)return C;let L=V!==void 0?H._$Co?.[V]:H._$Cl,r=M1(C)?void 0:C._$litDirective$;return L?.constructor!==r&&(L?._$AO?.(!1),r===void 0?L=void 0:(L=new r(M),L._$AT(M,H,V)),V!==void 0?(H._$Co??=[])[V]=L:H._$Cl=L),L!==void 0&&(C=z(M,L._$AS(M,C.values),L,V)),C}var b1=class{constructor(C,H){this._$AV=[],this._$AN=void 0,this._$AD=C,this._$AM=H}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(C){let{el:{content:H},parts:V}=this._$AD,L=(C?.creationScope??F).importNode(H,!0);R.currentNode=L;let r=R.nextNode(),e=0,t=0,i=V[0];for(;i!==void 0;){if(e===i.index){let A;i.type===2?A=new e1(r,r.nextSibling,this,C):i.type===1?A=new i.ctor(r,i.name,i.strings,this,C):i.type===6&&(A=new P1(r,this,C)),this._$AV.push(A),i=V[++t]}e!==i?.index&&(r=R.nextNode(),e++)}return R.currentNode=F,L}p(C){let H=0;for(let V of this._$AV)V!==void 0&&(V.strings!==void 0?(V._$AI(C,V,H),H+=V.strings.length-2):V._$AI(C[H])),H++}},e1=class M{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(C,H,V,L){this.type=2,this._$AH=a,this._$AN=void 0,this._$AA=C,this._$AB=H,this._$AM=V,this.options=L,this._$Cv=L?.isConnected??!0}get parentNode(){let C=this._$AA.parentNode,H=this._$AM;return H!==void 0&&C?.nodeType===11&&(C=H.parentNode),C}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(C,H=this){C=z(this,C,H),M1(C)?C===a||C==null||C===""?(this._$AH!==a&&this._$AR(),this._$AH=a):C!==this._$AH&&C!==D&&this._(C):C._$litType$!==void 0?this.$(C):C.nodeType!==void 0?this.T(C):A5(C)?this.k(C):this._(C)}O(C){return this._$AA.parentNode.insertBefore(C,this._$AB)}T(C){this._$AH!==C&&(this._$AR(),this._$AH=this.O(C))}_(C){this._$AH!==a&&M1(this._$AH)?this._$AA.nextSibling.data=C:this.T(F.createTextNode(C)),this._$AH=C}$(C){let{values:H,_$litType$:V}=C,L=typeof V=="number"?this._$AC(C):(V.el===void 0&&(V.el=r1.createElement(e2(V.h,V.h[0]),this.options)),V);if(this._$AH?._$AD===L)this._$AH.p(H);else{let r=new b1(L,this),e=r.u(this.options);r.p(H),this.T(e),this._$AH=r}}_$AC(C){let H=V2.get(C.strings);return H===void 0&&V2.set(C.strings,H=new r1(C)),H}k(C){_1(this._$AH)||(this._$AH=[],this._$AR());let H=this._$AH,V,L=0;for(let r of C)L===H.length?H.push(V=new M(this.O(L1()),this.O(L1()),this,this.options)):V=H[L],V._$AI(r),L++;L<H.length&&(this._$AR(V&&V._$AB.nextSibling,L),H.length=L)}_$AR(C=this._$AA.nextSibling,H){for(this._$AP?.(!1,!0,H);C!==this._$AB;){let V=j1(C).nextSibling;j1(C).remove(),C=V}}setConnected(C){this._$AM===void 0&&(this._$Cv=C,this._$AP?.(C))}},U=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(C,H,V,L,r){this.type=1,this._$AH=a,this._$AN=void 0,this.element=C,this.name=H,this._$AM=L,this.options=r,V.length>2||V[0]!==""||V[1]!==""?(this._$AH=Array(V.length-1).fill(new String),this.strings=V):this._$AH=a}_$AI(C,H=this,V,L){let r=this.strings,e=!1;if(r===void 0)C=z(this,C,H,0),e=!M1(C)||C!==this._$AH&&C!==D,e&&(this._$AH=C);else{let t=C,i,A;for(C=r[0],i=0;i<r.length-1;i++)A=z(this,t[V+i],H,i),A===D&&(A=this._$AH[i]),e||=!M1(A)||A!==this._$AH[i],A===a?C=a:C!==a&&(C+=(A??"")+r[i+1]),this._$AH[i]=A}e&&!L&&this.j(C)}j(C){C===a?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,C??"")}},w1=class extends U{constructor(){super(...arguments),this.type=3}j(C){this.element[this.name]=C===a?void 0:C}},y1=class extends U{constructor(){super(...arguments),this.type=4}j(C){this.element.toggleAttribute(this.name,!!C&&C!==a)}},B1=class extends U{constructor(C,H,V,L,r){super(C,H,V,L,r),this.type=5}_$AI(C,H=this){if((C=z(this,C,H,0)??a)===D)return;let V=this._$AH,L=C===a&&V!==a||C.capture!==V.capture||C.once!==V.once||C.passive!==V.passive,r=C!==a&&(V===a||L);L&&this.element.removeEventListener(this.name,this,V),r&&this.element.addEventListener(this.name,this,C),this._$AH=C}handleEvent(C){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,C):this._$AH.handleEvent(C)}},P1=class{constructor(C,H,V){this.element=C,this.type=6,this._$AN=void 0,this._$AM=H,this.options=V}get _$AU(){return this._$AM._$AU}_$AI(C){z(this,C)}};var p5=T1.litHtmlPolyfillSupport;p5?.(r1,e1),(T1.litHtmlVersions??=[]).push("3.3.3");var t2=(M,C,H)=>{let V=H?.renderBefore??C,L=V._$litPart$;if(L===void 0){let r=H?.renderBefore??null;V._$litPart$=L=new e1(C.insertBefore(L1(),r),r,void 0,H??{})}return L._$AI(M),L};var F1=globalThis,Z=class extends g{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let C=super.createRenderRoot();return this.renderOptions.renderBefore??=C.firstChild,C}update(C){let H=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(C),this._$Do=t2(H,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return D}};Z._$litElement$=!0,Z.finalized=!0,F1.litElementHydrateSupport?.({LitElement:Z});var m5=F1.litElementPolyfillSupport;m5?.({LitElement:Z});(F1.litElementVersions??=[]).push("4.2.2");var i2="M4.93,4.93C3.12,6.74 2,9.24 2,12C2,14.76 3.12,17.26 4.93,19.07L6.34,17.66C4.89,16.22 4,14.22 4,12C4,9.79 4.89,7.78 6.34,6.34L4.93,4.93M19.07,4.93L17.66,6.34C19.11,7.78 20,9.79 20,12C20,14.22 19.11,16.22 17.66,17.66L19.07,19.07C20.88,17.26 22,14.76 22,12C22,9.24 20.88,6.74 19.07,4.93M7.76,7.76C6.67,8.85 6,10.35 6,12C6,13.65 6.67,15.15 7.76,16.24L9.17,14.83C8.45,14.11 8,13.11 8,12C8,10.89 8.45,9.89 9.17,9.17L7.76,7.76M16.24,7.76L14.83,9.17C15.55,9.89 16,10.89 16,12C16,13.11 15.55,14.11 14.83,14.83L16.24,16.24C17.33,15.15 18,13.65 18,12C18,10.35 17.33,8.85 16.24,7.76M12,10A2,2 0 0,0 10,12A2,2 0 0,0 12,14A2,2 0 0,0 14,12A2,2 0 0,0 12,10Z";var o2="M11,15H13V17H11V15M11,7H13V13H11V7M12,2C6.47,2 2,6.5 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20Z";var a2="M11,4H13V16L18.5,10.5L19.92,11.92L12,19.84L4.08,11.92L5.5,10.5L11,16V4Z";var A2="M13,20H11V8L5.5,13.5L4.08,12.08L12,4.16L19.92,12.08L18.5,13.5L13,8V20Z";var D1="M18,11H6V6H18M16.5,17A1.5,1.5 0 0,1 15,15.5A1.5,1.5 0 0,1 16.5,14A1.5,1.5 0 0,1 18,15.5A1.5,1.5 0 0,1 16.5,17M7.5,17A1.5,1.5 0 0,1 6,15.5A1.5,1.5 0 0,1 7.5,14A1.5,1.5 0 0,1 9,15.5A1.5,1.5 0 0,1 7.5,17M4,16C4,16.88 4.39,17.67 5,18.22V20A1,1 0 0,0 6,21H7A1,1 0 0,0 8,20V19H16V20A1,1 0 0,0 17,21H18A1,1 0 0,0 19,20V18.22C19.61,17.67 20,16.88 20,16V6C20,2.5 16.42,2 12,2C7.58,2 4,2.5 4,6V16Z";var d2="M16.5,4V8.25L19.36,9.94L18.61,11.16L15,9V4H16.5M16,13C17.36,13 18.54,12.5 19.5,11.53C20.5,10.56 21,9.39 21,8C21,6.64 20.5,5.46 19.5,4.5C18.54,3.5 17.36,3 16,3C14.61,3 13.44,3.5 12.47,4.5C11.5,5.46 11,6.64 11,8C11,9.39 11.5,10.56 12.47,11.53C13.44,12.5 14.61,13 16,13M13.5,19C13.94,19 14.3,18.84 14.58,18.54C14.86,18.24 15,17.89 15,17.5C15,17.08 14.86,16.73 14.58,16.43C14.3,16.13 13.94,16 13.5,16C13.06,16 12.7,16.13 12.42,16.43C12.14,16.73 12,17.08 12,17.5C12,17.89 12.14,18.24 12.42,18.54C12.7,18.84 13.06,19 13.5,19M3,13H11.11C9.7,11.64 9,10 9,8H3V13M4.5,19C4.94,19 5.3,18.84 5.58,18.54C5.86,18.24 6,17.89 6,17.5C6,17.08 5.86,16.73 5.58,16.43C5.3,16.13 4.94,16 4.5,16C4.06,16 3.7,16.13 3.42,16.43C3.14,16.73 3,17.08 3,17.5C3,17.89 3.14,18.24 3.42,18.54C3.7,18.84 4.06,19 4.5,19M16,1C17.92,1 19.58,1.67 20.95,3.05C22.33,4.42 23,6.08 23,8C23,9.77 22.44,11.29 21.28,12.59C20.13,13.88 18.7,14.66 17,14.91V18C17,18.84 16.67,19.58 16,20.2V22C16,22.27 15.89,22.5 15.7,22.71C15.5,22.91 15.28,23 15,23H14C13.73,23 13.5,22.91 13.29,22.71C13.09,22.5 13,22.27 13,22V21H5V22C5,22.27 4.91,22.5 4.71,22.71C4.5,22.91 4.27,23 4,23H3C2.72,23 2.5,22.91 2.3,22.71C2.11,22.5 2,22.27 2,22V20.2C1.33,19.58 1,18.84 1,18V8C1,6.42 1.67,5.35 3.05,4.8C4.42,4.26 6.41,4 9,4C9.13,4 9.33,4 9.61,4C9.89,4 10.09,4.03 10.22,4.03C11.63,2 13.55,1 16,1Z";var p2="M22 7V16C22 16.71 21.62 17.36 21 17.72V19.25C21 19.66 20.66 20 20.25 20H19.75C19.34 20 19 19.66 19 19.25V18H12V19.25C12 19.66 11.66 20 11.25 20H10.75C10.34 20 10 19.66 10 19.25V17.72C9.39 17.36 9 16.71 9 16V7C9 4 12 4 15.5 4S22 4 22 7M13 15C13 14.45 12.55 14 12 14S11 14.45 11 15 11.45 16 12 16 13 15.55 13 15M20 15C20 14.45 19.55 14 19 14S18 14.45 18 15 18.45 16 19 16 20 15.55 20 15M20 7H11V11H20V7M7 9.5C6.97 8.12 5.83 7 4.45 7.05C3.07 7.08 1.97 8.22 2 9.6C2.03 10.77 2.86 11.77 4 12V20H5V12C6.18 11.76 7 10.71 7 9.5Z";var m2="M15,13H16.5V15.82L18.94,17.23L18.19,18.53L15,16.69V13M19,8H5V19H9.67C9.24,18.09 9,17.07 9,16A7,7 0 0,1 16,9C17.07,9 18.09,9.24 19,9.67V8M5,21C3.89,21 3,20.1 3,19V5C3,3.89 3.89,3 5,3H6V1H8V3H16V1H18V3H19A2,2 0 0,1 21,5V11.1C22.24,12.36 23,14.09 23,16A7,7 0 0,1 16,23C14.09,23 12.36,22.24 11.1,21H5M16,11.15A4.85,4.85 0 0,0 11.15,16C11.15,18.68 13.32,20.85 16,20.85A4.85,4.85 0 0,0 20.85,16C20.85,13.32 18.68,11.15 16,11.15Z";var n2="M8.59,16.58L13.17,12L8.59,7.41L10,6L16,12L10,18L8.59,16.58Z";var l2="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z";var v2="M21.86 12.5C21.1 11.63 20.15 11.13 19 11C19 9.05 18.32 7.4 16.96 6.04C15.6 4.68 13.95 4 12 4C10.42 4 9 4.47 7.75 5.43S5.67 7.62 5.25 9.15C4 9.43 2.96 10.08 2.17 11.1S1 13.28 1 14.58C1 16.09 1.54 17.38 2.61 18.43C3.69 19.5 5 20 6.5 20H18.5C19.75 20 20.81 19.56 21.69 18.69C22.56 17.81 23 16.75 23 15.5C23 14.35 22.62 13.35 21.86 12.5M20.27 17.27C19.79 17.76 19.2 18 18.5 18H6.5C5.53 18 4.71 17.66 4.03 17C3.34 16.29 3 15.47 3 14.5S3.34 12.71 4.03 12.03C4.71 11.34 5.53 11 6.5 11H7C7 9.62 7.5 8.44 8.46 7.46C9.44 6.5 10.62 6 12 6S14.56 6.5 15.54 7.46C16.5 8.44 17 9.62 17 11V13H18.5C19.2 13 19.79 13.24 20.27 13.73S21 14.8 21 15.5 20.76 16.79 20.27 17.27M11 15H13V17H11V15M11 7H13V13H11V7Z";var x2="M12,8A4,4 0 0,1 16,12A4,4 0 0,1 12,16A4,4 0 0,1 8,12A4,4 0 0,1 12,8M3.05,13H1V11H3.05C3.5,6.83 6.83,3.5 11,3.05V1H13V3.05C17.17,3.5 20.5,6.83 20.95,11H23V13H20.95C20.5,17.17 17.17,20.5 13,20.95V23H11V20.95C6.83,20.5 3.5,17.17 3.05,13M12,5A7,7 0 0,0 5,12A7,7 0 0,0 12,19A7,7 0 0,0 19,12A7,7 0 0,0 12,5Z";var Z2="M18,10H13V7.59L22.12,6.07L21.88,4.59L16.41,5.5C16.46,5.35 16.5,5.18 16.5,5A1.5,1.5 0 0,0 15,3.5A1.5,1.5 0 0,0 13.5,5C13.5,5.35 13.63,5.68 13.84,5.93L13,6.07V5H11V6.41L10.41,6.5C10.46,6.35 10.5,6.18 10.5,6A1.5,1.5 0 0,0 9,4.5A1.5,1.5 0 0,0 7.5,6C7.5,6.36 7.63,6.68 7.83,6.93L1.88,7.93L2.12,9.41L11,7.93V10H6C4.89,10 4,10.9 4,12V18A2,2 0 0,0 6,20H18A2,2 0 0,0 20,18V12A2,2 0 0,0 18,10M6,12H8.25V16H6V12M9.75,16V12H14.25V16H9.75M18,16H15.75V12H18V16Z";var s2="M11,9H13V7H11M12,20C7.59,20 4,16.41 4,12C4,7.59 7.59,4 12,4C16.41,4 20,7.59 20,12C20,16.41 16.41,20 12,20M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M11,17H13V11H11V17Z";var u2="M9.5,3A6.5,6.5 0 0,1 16,9.5C16,11.11 15.41,12.59 14.44,13.73L14.71,14H15.5L20.5,19L19,20.5L14,15.5V14.71L13.73,14.44C12.59,15.41 11.11,16 9.5,16A6.5,6.5 0 0,1 3,9.5A6.5,6.5 0 0,1 9.5,3M9.5,5C7,5 5,7 5,9.5C5,12 7,14 9.5,14C12,14 14,12 14,9.5C14,7 12,5 9.5,5Z";var S2="M12 2C8.14 2 5 5.14 5 9C5 14.25 12 22 12 22S19 14.25 19 9C19 5.14 15.86 2 12 2M12 4C13.1 4 14 4.9 14 6C14 7.11 13.1 8 12 8S10 7.11 10 6C10 4.9 10.9 4 12 4M12 14C10.33 14 8.86 13.15 8 11.85C8 10.53 10.67 9.8 12 9.8S16 10.53 16 11.85C15.14 13.15 13.67 14 12 14Z";var c2="M20 19.7L3.3 3L2 4.3L5.2 7.5C5.1 8 5 8.5 5 9C5 14.2 12 22 12 22S13.7 20.1 15.4 17.6L18.8 21L20 19.7M12 18.7C7.4 12.5 7 10.4 7 9.3L13.8 16.1C13.3 16.9 12.7 17.7 12 18.7M8.4 5.6L7 4.2C8.2 2.8 10 2 12 2C15.9 2 19 5.1 19 9C19 10.7 18.3 12.6 17.3 14.5L15.8 13C17 10.6 17 9.6 17 9C17 6.2 14.8 4 12 4C10.6 4 9.3 4.6 8.4 5.6M12 6.5C13.4 6.5 14.5 7.6 14.5 9C14.5 9.7 14.2 10.4 13.7 10.9L10.2 7.4C10.6 6.8 11.3 6.5 12 6.5Z";var h2="M20.5,3L20.34,3.03L15,5.1L9,3L3.36,4.9C3.15,4.97 3,5.15 3,5.38V20.5A0.5,0.5 0 0,0 3.5,21L3.66,20.97L9,18.9L15,21L20.64,19.1C20.85,19.03 21,18.85 21,18.62V3.5A0.5,0.5 0 0,0 20.5,3M10,5.47L14,6.87V18.53L10,17.13V5.47M5,6.46L8,5.45V17.15L5,18.31V6.46M19,17.54L16,18.55V6.86L19,5.7V17.54Z";var O2="M5,11L6.5,6.5H17.5L19,11M17.5,16A1.5,1.5 0 0,1 16,14.5A1.5,1.5 0 0,1 17.5,13A1.5,1.5 0 0,1 19,14.5A1.5,1.5 0 0,1 17.5,16M6.5,16A1.5,1.5 0 0,1 5,14.5A1.5,1.5 0 0,1 6.5,13A1.5,1.5 0 0,1 8,14.5A1.5,1.5 0 0,1 6.5,16M18.92,6C18.72,5.42 18.16,5 17.5,5H15V3H9V5H6.5C5.84,5 5.28,5.42 5.08,6L3,12V20A1,1 0 0,0 4,21H5A1,1 0 0,0 6,20V19H18V20A1,1 0 0,0 19,21H20A1,1 0 0,0 21,20V12L18.92,6Z";var f2="M6,2V8H6V8L10,12L6,16V16H6V22H18V16H18V16L14,12L18,8V8H18V2H6M16,16.5V20H8V16.5L12,12.5L16,16.5M12,11.5L8,7.5V4H16V7.5L12,11.5Z";var g2="M12,2C8,2 4,2.5 4,6V15.5A3.5,3.5 0 0,0 7.5,19L6,20.5V21H8.23L10.23,19H14L16,21H18V20.5L16.5,19A3.5,3.5 0 0,0 20,15.5V6C20,2.5 16.42,2 12,2M7.5,17A1.5,1.5 0 0,1 6,15.5A1.5,1.5 0 0,1 7.5,14A1.5,1.5 0 0,1 9,15.5A1.5,1.5 0 0,1 7.5,17M11,10H6V6H11V10M13,10V6H18V10H13M16.5,17A1.5,1.5 0 0,1 15,15.5A1.5,1.5 0 0,1 16.5,14A1.5,1.5 0 0,1 18,15.5A1.5,1.5 0 0,1 16.5,17Z";var k2="M19,16.94V8.5C19,5.71 16.39,5.1 13,5L13.75,3.5H17V2H7V3.5H11.75L11,5C7.86,5.11 5,5.73 5,8.5V16.94C5,18.39 6.19,19.6 7.59,19.91L6,21.5V22H8.23L10.23,20H14L16,22H18V21.5L16.5,20H16.42C18.11,20 19,18.63 19,16.94M12,18.5A1.5,1.5 0 0,1 10.5,17A1.5,1.5 0 0,1 12,15.5A1.5,1.5 0 0,1 13.5,17A1.5,1.5 0 0,1 12,18.5M17,14H7V9H17V14Z";var m={live:i2,alert:o2,arrowDown:a2,arrowUp:A2,busStop:p2,timetable:m2,chevron:n2,close:l2,offline:v2,recenter:x2,info:s2,search:u2,myStop:S2,noPosition:c2,map:h2,empty:f2},n5={0:k2,2:g2,3:D1,5:Z2,8:O2,715:d2},G=M=>n5[M]??D1,n=(M,{size:C=20,label:H,cls:V="icon"}={})=>o`<svg
    class=${V}
    viewBox="0 0 24 24"
    width=${C}
    height=${C}
    role=${H?"img":"presentation"}
    aria-hidden=${H?"false":"true"}
    aria-label=${H??""}
    focusable="false"
  ><path fill="currentColor" d=${M}></path></svg>`,E1=(M,C=18)=>`<svg viewBox="0 0 24 24" width="${C}" height="${C}" aria-hidden="true" focusable="false"><path fill="currentColor" d="${M}"/></svg>`;var b2={he:{name:"Israel Transit",description:"\u05D6\u05DE\u05E0\u05D9 \u05D4\u05D2\u05E2\u05D4 \u05D1\u05D6\u05DE\u05DF \u05D0\u05DE\u05EA \u05DC\u05EA\u05D7\u05D1\u05D5\u05E8\u05D4 \u05D4\u05E6\u05D9\u05D1\u05D5\u05E8\u05D9\u05EA \u05D1\u05D9\u05E9\u05E8\u05D0\u05DC",scheduled:"\u05DC\u05E4\u05D9 \u05DC\u05D5\u05D7 \u05D6\u05DE\u05E0\u05D9\u05DD",now:"\u05E2\u05DB\u05E9\u05D9\u05D5",minutes:"\u05D3\u05E7\u05F3",minutesLong:"\u05D3\u05E7\u05D5\u05EA",noArrivals:"\u05D0\u05D9\u05DF \u05D4\u05D2\u05E2\u05D5\u05EA \u05E7\u05E8\u05D5\u05D1\u05D5\u05EA",noRealtime:"\u05D0\u05D9\u05DF \u05DB\u05E8\u05D2\u05E2 \u05E0\u05EA\u05D5\u05E0\u05D9 \u05D6\u05DE\u05DF \u05D0\u05DE\u05EA \u05DC\u05EA\u05D7\u05E0\u05D4 \u05D4\u05D6\u05D5",noData:"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9\u05DD \u05D6\u05DE\u05D9\u05E0\u05D9\u05DD \u05DC\u05EA\u05D7\u05E0\u05D4 \u05D4\u05D6\u05D5",loading:"\u05D8\u05D5\u05E2\u05DF\u2026",staleData:"\u05D0\u05D9\u05DF \u05D7\u05D9\u05D1\u05D5\u05E8 \u05DB\u05E8\u05D2\u05E2. \u05DE\u05D5\u05E6\u05D2\u05D9\u05DD \u05D4\u05D6\u05DE\u05E0\u05D9\u05DD \u05D4\u05D0\u05D7\u05E8\u05D5\u05E0\u05D9\u05DD \u05E9\u05D4\u05EA\u05E7\u05D1\u05DC\u05D5.",errorUnknownStop:"\u05D4\u05EA\u05D7\u05E0\u05D4 \u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D4. \u05D1\u05D3\u05E7\u05D5 \u05D0\u05EA \u05E7\u05D5\u05D3 \u05D4\u05EA\u05D7\u05E0\u05D4 \u05D1\u05D4\u05D2\u05D3\u05E8\u05D5\u05EA \u05D4\u05DB\u05E8\u05D8\u05D9\u05E1.",errorNotLoaded:"\u05D4\u05D0\u05D9\u05E0\u05D8\u05D2\u05E8\u05E6\u05D9\u05D4 Israel Transit \u05DC\u05D0 \u05E4\u05E2\u05D9\u05DC\u05D4. \u05D1\u05D3\u05E7\u05D5 \u05D0\u05D5\u05EA\u05D4 \u05D1\u05D4\u05D2\u05D3\u05E8\u05D5\u05EA.",errorIndex:"\u05DC\u05D5\u05D7 \u05D4\u05D6\u05DE\u05E0\u05D9\u05DD \u05D4\u05DE\u05E7\u05D5\u05DE\u05D9 \u05E2\u05D3\u05D9\u05D9\u05DF \u05DC\u05D0 \u05DE\u05D5\u05DB\u05DF. \u05E0\u05E1\u05D5 \u05E9\u05D5\u05D1 \u05D1\u05E2\u05D5\u05D3 \u05DB\u05DE\u05D4 \u05D3\u05E7\u05D5\u05EA.",errorConnection:"\u05D4\u05D7\u05D9\u05D1\u05D5\u05E8 \u05DC-Home Assistant \u05D4\u05EA\u05E0\u05EA\u05E7. \u05DE\u05EA\u05D7\u05D1\u05E8 \u05DE\u05D7\u05D3\u05E9\u2026",errorGeneric:"\u05DC\u05D0 \u05E0\u05D9\u05EA\u05DF \u05DC\u05D8\u05E2\u05D5\u05DF \u05DB\u05E8\u05D2\u05E2 \u05D0\u05EA \u05D6\u05DE\u05E0\u05D9 \u05D4\u05D4\u05D2\u05E2\u05D4.",stop:"\u05EA\u05D7\u05E0\u05D4",stopDetails:"\u05E4\u05E8\u05D8\u05D9 \u05D4\u05EA\u05D7\u05E0\u05D4",allLines:"\u05DB\u05DC \u05D4\u05E7\u05D5\u05D5\u05D9\u05DD \u05D1\u05EA\u05D7\u05E0\u05D4",lineDetails:"\u05E4\u05E8\u05D8\u05D9 \u05D4\u05E7\u05D5",routeStops:"\u05EA\u05D7\u05E0\u05D5\u05EA \u05D4\u05E7\u05D5",vehicleHere:"\u05D4\u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E0\u05D5\u05DB\u05D7\u05D9",myStop:"\u05D4\u05EA\u05D7\u05E0\u05D4 \u05E9\u05DC\u05DA",departedAt:"\u05D9\u05E6\u05D0 \u05D1\u05BE",platform:"\u05E8\u05E6\u05D9\u05E3",delay:"\u05E2\u05D9\u05DB\u05D5\u05D1",delayMinutes:"\u05D3\u05E7\u05F3 \u05E2\u05D9\u05DB\u05D5\u05D1",onTime:"\u05D1\u05D6\u05DE\u05DF",operator:"\u05DE\u05E4\u05E2\u05D9\u05DC",destination:"\u05D9\u05E2\u05D3",noLines:"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D5 \u05E7\u05D5\u05D5\u05D9\u05DD \u05D1\u05EA\u05D7\u05E0\u05D4 \u05D4\u05D6\u05D5",noRouteStops:"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0 \u05DE\u05E1\u05DC\u05D5\u05DC \u05DC\u05E7\u05D5 \u05D4\u05D6\u05D4",close:"\u05E1\u05D2\u05D9\u05E8\u05D4",live:"\u05D1\u05D6\u05DE\u05DF \u05D0\u05DE\u05EA",emptyTitle:"\u05D0\u05D9\u05DF \u05DE\u05D4 \u05DC\u05D4\u05E6\u05D9\u05D2 \u05DB\u05E8\u05D2\u05E2",errorTitle:"\u05DC\u05D0 \u05E0\u05D9\u05EA\u05DF \u05DC\u05D8\u05E2\u05D5\u05DF",vehicleMap:"\u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E8\u05DB\u05D1",routeLine:"\u05DE\u05E1\u05DC\u05D5\u05DC \u05D4\u05E7\u05D5",noVehicleLocation:"\u05D4\u05DE\u05E4\u05E2\u05D9\u05DC \u05D0\u05D9\u05E0\u05D5 \u05DE\u05E9\u05D3\u05E8 \u05D0\u05EA \u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E8\u05DB\u05D1",vehicleOf:"\u05E7\u05D5 {line}, \u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E8\u05DB\u05D1",vehicleStale:"\u05E7\u05D5 {line}, \u05DE\u05D9\u05E7\u05D5\u05DD \u05D0\u05D7\u05E8\u05D5\u05DF \u05D9\u05D3\u05D5\u05E2",nearStop:"\u05DC\u05D9\u05D3 {stop}",awayFromRoute:"\u05D4\u05E8\u05DB\u05D1 \u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0 \u05E2\u05DC \u05D4\u05DE\u05E1\u05DC\u05D5\u05DC",stopsToGo:"\u05E2\u05D5\u05D3 {n} \u05EA\u05D7\u05E0\u05D5\u05EA \u05E2\u05D3 \u05D4\u05EA\u05D7\u05E0\u05D4 \u05E9\u05DC\u05DA",stopsToGoOne:"\u05D4\u05EA\u05D7\u05E0\u05D4 \u05D4\u05D1\u05D0\u05D4 \u05D4\u05D9\u05D0 \u05D4\u05EA\u05D7\u05E0\u05D4 \u05E9\u05DC\u05DA",atYourStop:"\u05D4\u05E8\u05DB\u05D1 \u05D1\u05EA\u05D7\u05E0\u05D4 \u05E9\u05DC\u05DA",positionAge:"\u05DE\u05D9\u05E7\u05D5\u05DD \u05DE\u05DC\u05E4\u05E0\u05D9 {n} \u05D3\u05E7\u05F3",positionAgeSeconds:"\u05DE\u05D9\u05E7\u05D5\u05DD \u05DE\u05DC\u05E4\u05E0\u05D9 \u05E4\u05D7\u05D5\u05EA \u05DE\u05D3\u05E7\u05D4",approximateRoute:"\u05D4\u05DE\u05E1\u05DC\u05D5\u05DC \u05DE\u05E9\u05D5\u05E2\u05E8: \u05E7\u05D5\u05D5\u05D9\u05DD \u05D9\u05E9\u05E8\u05D9\u05DD \u05D1\u05D9\u05DF \u05D4\u05EA\u05D7\u05E0\u05D5\u05EA",arrivesAt:"\u05DE\u05D2\u05D9\u05E2 \u05D0\u05DC\u05D9\u05DA \u05D1\u05BE{time}",mapUnavailable:"\u05D4\u05DE\u05E4\u05D4 \u05DC\u05D0 \u05D6\u05DE\u05D9\u05E0\u05D4 \u05DB\u05E8\u05D2\u05E2. \u05E8\u05E9\u05D9\u05DE\u05EA \u05D4\u05EA\u05D7\u05E0\u05D5\u05EA \u05DC\u05DE\u05D8\u05D4 \u05E2\u05D3\u05D9\u05D9\u05DF \u05E2\u05D3\u05DB\u05E0\u05D9\u05EA.",mapUnsupported:"\u05D4\u05D3\u05E4\u05D3\u05E4\u05DF \u05D4\u05D6\u05D4 \u05DC\u05D0 \u05D9\u05DB\u05D5\u05DC \u05DC\u05D4\u05E6\u05D9\u05D2 \u05D0\u05EA \u05D4\u05DE\u05E4\u05D4. \u05E8\u05E9\u05D9\u05DE\u05EA \u05D4\u05EA\u05D7\u05E0\u05D5\u05EA \u05DC\u05DE\u05D8\u05D4 \u05DE\u05E6\u05D9\u05D2\u05D4 \u05D0\u05EA \u05D0\u05D5\u05EA\u05D5 \u05DE\u05D9\u05D3\u05E2.",mapFailed:"\u05D4\u05DE\u05E4\u05D4 \u05D4\u05E4\u05E1\u05D9\u05E7\u05D4 \u05DC\u05E2\u05D1\u05D5\u05D3.",mapVendor:"\u05D4\u05DE\u05E4\u05D4 \u05DC\u05D0 \u05E0\u05D8\u05E2\u05E0\u05D4, \u05DB\u05E0\u05E8\u05D0\u05D4 \u05DB\u05D9 \u05D4\u05DB\u05E8\u05D8\u05D9\u05E1 \u05D4\u05EA\u05E2\u05D3\u05DB\u05DF. \u05E6\u05E8\u05D9\u05DA \u05DC\u05E8\u05E2\u05E0\u05DF \u05D0\u05EA \u05D4\u05D3\u05E3.",retry:"\u05E0\u05D9\u05E1\u05D9\u05D5\u05DF \u05D7\u05D5\u05D6\u05E8",reload:"\u05E8\u05E2\u05E0\u05D5\u05DF \u05D4\u05D3\u05E3",recenter:"\u05D7\u05D6\u05E8\u05D4 \u05DC\u05E8\u05DB\u05D1",zoomIn:"\u05D4\u05EA\u05E7\u05E8\u05D1\u05D5\u05EA",zoomOut:"\u05D4\u05EA\u05E8\u05D7\u05E7\u05D5\u05EA",attribution:"\u05E7\u05E8\u05D3\u05D9\u05D8\u05D9\u05DD \u05E9\u05DC \u05D4\u05DE\u05E4\u05D4",mapLabel:"\u05DE\u05E4\u05EA \u05D4\u05DE\u05E1\u05DC\u05D5\u05DC",showOnMap:"\u05D4\u05E6\u05D2\u05D4 \u05D1\u05DE\u05E4\u05D4",editorStop:"\u05EA\u05D7\u05E0\u05D4",editorSearch:"\u05D7\u05D9\u05E4\u05D5\u05E9 \u05EA\u05D7\u05E0\u05D4 \u05DC\u05E4\u05D9 \u05E9\u05DD, \u05E2\u05D9\u05E8, \u05E8\u05D7\u05D5\u05D1 \u05D0\u05D5 \u05E7\u05D5\u05D3",editorSearchHelp:'\u05D0\u05E4\u05E9\u05E8 \u05DC\u05E9\u05DC\u05D1 \u05DE\u05D9\u05DC\u05D9\u05DD, \u05DC\u05DE\u05E9\u05DC "\u05DB\u05E4\u05E8 \u05E1\u05D1\u05D0 \u05D5\u05D9\u05E6\u05DE\u05DF"',editorSearching:"\u05DE\u05D7\u05E4\u05E9\u2026",editorNoResults:"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D5 \u05EA\u05D7\u05E0\u05D5\u05EA",editorLines:"\u05E7\u05D5\u05D5\u05D9\u05DD \u05DC\u05D4\u05E6\u05D2\u05D4",editorLinesHelp:"\u05D1\u05DC\u05D9 \u05D1\u05D7\u05D9\u05E8\u05D4 \u05D9\u05D5\u05E6\u05D2\u05D5 \u05DB\u05DC \u05D4\u05E7\u05D5\u05D5\u05D9\u05DD \u05D1\u05EA\u05D7\u05E0\u05D4",editorAddLine:"\u05D4\u05D5\u05E1\u05E4\u05EA \u05E7\u05D5",editorAllShown:"\u05DB\u05DC \u05D4\u05E7\u05D5\u05D5\u05D9\u05DD \u05D1\u05EA\u05D7\u05E0\u05D4 \u05DB\u05D1\u05E8 \u05D1\u05E8\u05E9\u05D9\u05DE\u05D4",editorMoveUp:"\u05D4\u05E2\u05D1\u05E8\u05D4 \u05DC\u05DE\u05E2\u05DC\u05D4",editorMoveDown:"\u05D4\u05E2\u05D1\u05E8\u05D4 \u05DC\u05DE\u05D8\u05D4",editorRemove:"\u05D4\u05E1\u05E8\u05D4",editorTitle:"\u05DB\u05D5\u05EA\u05E8\u05EA \u05DE\u05D5\u05EA\u05D0\u05DE\u05EA",editorMaxArrivals:"\u05DE\u05E1\u05E4\u05E8 \u05D4\u05D2\u05E2\u05D5\u05EA \u05DE\u05E8\u05D1\u05D9",editorMaxLines:"\u05DE\u05E1\u05E4\u05E8 \u05E7\u05D5\u05D5\u05D9\u05DD \u05DE\u05E8\u05D1\u05D9",editorMaxLinesHelp:"\u200F0 = \u05DC\u05DC\u05D0 \u05D4\u05D2\u05D1\u05DC\u05D4",editorOrder:"\u05E1\u05D3\u05E8 \u05D4\u05D4\u05E6\u05D2\u05D4",editorOrderTime:"\u05DC\u05E4\u05D9 \u05D6\u05DE\u05DF \u05D4\u05D4\u05D2\u05E2\u05D4",editorOrderLines:"\u05DC\u05E4\u05D9 \u05E1\u05D3\u05E8 \u05D4\u05E7\u05D5\u05D5\u05D9\u05DD \u05E9\u05E0\u05D1\u05D7\u05E8",editorDisplay:"\u05E4\u05E8\u05D8\u05D9\u05DD \u05DC\u05D4\u05E6\u05D2\u05D4",editorShowHeader:"\u05DB\u05D5\u05EA\u05E8\u05EA \u05D4\u05EA\u05D7\u05E0\u05D4",editorShowCity:"\u05E9\u05DD \u05D4\u05E2\u05D9\u05E8",editorShowStopCode:"\u05E7\u05D5\u05D3 \u05D4\u05EA\u05D7\u05E0\u05D4",editorShowDestination:"\u05D9\u05E2\u05D3 \u05D4\u05E7\u05D5",editorShowOperator:"\u05E9\u05DD \u05D4\u05DE\u05E4\u05E2\u05D9\u05DC",editorShowModeIcon:"\u05E1\u05DE\u05DC \u05E1\u05D5\u05D2 \u05D4\u05EA\u05D7\u05D1\u05D5\u05E8\u05D4",editorShowRealtimeTag:'\u05EA\u05D5\u05D5\u05D9\u05EA "\u05DC\u05E4\u05D9 \u05DC\u05D5\u05D7 \u05D6\u05DE\u05E0\u05D9\u05DD"',editorShowPlatform:"\u05E8\u05E6\u05D9\u05E3",editorShowDelay:"\u05E2\u05D9\u05DB\u05D5\u05D1",editorShowClock:"\u05E9\u05E2\u05EA \u05D4\u05D2\u05E2\u05D4 \u05DE\u05D3\u05D5\u05D9\u05E7\u05EA",editorShowMap:"\u05DE\u05E4\u05D4 \u05E2\u05DD \u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E8\u05DB\u05D1",editorShowMapHelp:"\u05E0\u05E4\u05EA\u05D7\u05EA \u05D1\u05E4\u05E8\u05D8\u05D9 \u05D4\u05E7\u05D5, \u05DB\u05E9\u05D4\u05DE\u05E4\u05E2\u05D9\u05DC \u05DE\u05E9\u05D3\u05E8 \u05DE\u05D9\u05E7\u05D5\u05DD",editorChange:"\u05E9\u05D9\u05E0\u05D5\u05D9 \u05EA\u05D7\u05E0\u05D4",editorCancel:"\u05D1\u05D9\u05D8\u05D5\u05DC",editorNoStop:"\u05DC\u05D0 \u05E0\u05D1\u05D7\u05E8\u05D4 \u05EA\u05D7\u05E0\u05D4",errorNoStop:"\u05D9\u05E9 \u05DC\u05D4\u05D2\u05D3\u05D9\u05E8 \u05E7\u05D5\u05D3 \u05EA\u05D7\u05E0\u05D4 (stop_code)",mode_0:"\u05E8\u05DB\u05D1\u05EA \u05E7\u05DC\u05D4",mode_2:"\u05E8\u05DB\u05D1\u05EA \u05D9\u05E9\u05E8\u05D0\u05DC",mode_3:"\u05D0\u05D5\u05D8\u05D5\u05D1\u05D5\u05E1",mode_5:"\u05E8\u05DB\u05D1\u05DC\u05D9\u05EA",mode_8:"\u05DE\u05D5\u05E0\u05D9\u05EA \u05E9\u05D9\u05E8\u05D5\u05EA",mode_715:"\u05E7\u05D5 \u05D2\u05DE\u05D9\u05E9"},en:{name:"Israel Transit",description:"Real-time Israeli public transport arrivals",scheduled:"Timetable",now:"Now",minutes:"min",minutesLong:"minutes",noArrivals:"No upcoming arrivals",noRealtime:"No real-time data for this stop right now",noData:"No data is published for this stop",loading:"Loading\u2026",staleData:"Offline right now. Showing the last times received.",errorUnknownStop:"Stop not found. Check the stop code in the card's settings.",errorNotLoaded:"The Israel Transit integration is not running. Check it in Settings.",errorIndex:"The local timetable is not ready yet. Try again in a few minutes.",errorConnection:"Lost the connection to Home Assistant. Reconnecting\u2026",errorGeneric:"Could not load arrival times right now.",stop:"Stop",stopDetails:"Stop details",allLines:"All lines at this stop",lineDetails:"Line details",routeStops:"Stops on this route",vehicleHere:"Current position",myStop:"Your stop",departedAt:"Departed at",platform:"Platform",delay:"Delay",delayMinutes:"min late",onTime:"On time",operator:"Operator",destination:"Destination",noLines:"No lines found at this stop",noRouteStops:"No route found for this line",close:"Close",live:"Real time",emptyTitle:"Nothing to show right now",errorTitle:"Could not load",vehicleMap:"Vehicle position",routeLine:"Route",noVehicleLocation:"The operator is not broadcasting this vehicle's position",vehicleOf:"Line {line}, vehicle position",vehicleStale:"Line {line}, last known position",nearStop:"Near {stop}",awayFromRoute:"The vehicle is not on the route",stopsToGo:"{n} stops to your stop",stopsToGoOne:"Your stop is next",atYourStop:"The vehicle is at your stop",positionAge:"Position from {n} min ago",positionAgeSeconds:"Position from less than a minute ago",approximateRoute:"Approximate route: straight lines between stops",arrivesAt:"Reaches you at {time}",mapUnavailable:"The map is not available right now. The stop list below is still current.",mapUnsupported:"This browser cannot show the map. The stop list below shows the same information.",mapFailed:"The map stopped working.",mapVendor:"The map did not load, probably because the card was updated. Reload the page.",retry:"Try again",reload:"Reload page",recenter:"Back to vehicle",zoomIn:"Zoom in",zoomOut:"Zoom out",attribution:"Map credits",mapLabel:"Route map",showOnMap:"Show on map",editorStop:"Stop",editorSearch:"Search by stop name, city, street or code",editorSearchHelp:'Words combine, for example "Kfar Saba Weizmann"',editorSearching:"Searching\u2026",editorNoResults:"No stops found",editorLines:"Lines to show",editorLinesHelp:"With nothing chosen, every line at the stop is shown",editorAddLine:"Add a line",editorAllShown:"Every line at this stop is already listed",editorMoveUp:"Move up",editorMoveDown:"Move down",editorRemove:"Remove",editorTitle:"Custom title",editorMaxArrivals:"Maximum arrivals",editorMaxLines:"Maximum lines",editorMaxLinesHelp:"0 = no limit",editorOrder:"Order",editorOrderTime:"By arrival time",editorOrderLines:"By the chosen line order",editorDisplay:"Details to show",editorShowHeader:"Stop header",editorShowCity:"City",editorShowStopCode:"Stop code",editorShowDestination:"Destination",editorShowOperator:"Operator name",editorShowModeIcon:"Mode icon",editorShowRealtimeTag:"Timetable tag",editorShowPlatform:"Platform",editorShowDelay:"Delay",editorShowClock:"Exact arrival time",editorShowMap:"Map with the vehicle position",editorShowMapHelp:"Opens in the line details, when a position is broadcast",editorChange:"Change stop",editorCancel:"Cancel",editorNoStop:"No stop selected",errorNoStop:"You need to define a stop_code",mode_0:"Light rail",mode_2:"Train",mode_3:"Bus",mode_5:"Cable car",mode_8:"Shared taxi",mode_715:"Flexible route"}},l5=M=>(M?.locale?.language||M?.language||"he").toLowerCase().startsWith("he")?"he":"en",S=(M,C,H)=>{let V=l5(M),L=b2[V][C]??b2.en[C]??C;return H?L.replace(/\{(\w+)\}/g,(r,e)=>e in H?String(H[e]):r):L};var k=([M,C])=>[C,M],s=M=>Array.isArray(M)&&Number.isFinite(M[0])&&Number.isFinite(M[1])&&!(M[0]===0&&M[1]===0),f=M=>M&&M.lat!=null&&M.lon!=null?[Number(M.lat),Number(M.lon)]:null,x1=(M,C)=>{let H=Math.cos((M[0]+C[0])/2*Math.PI/180),V=(C[0]-M[0])*111320,L=(C[1]-M[1])*111320*H;return Math.hypot(L,V)},w2=M=>{let C=(M||[]).filter(s),H=[0];for(let V=1;V<C.length;V++)H.push(H[V-1]+x1(C[V-1],C[V]));return{points:C,along:H,length:H[H.length-1]??0}};var $1=(M,C,H=0,V=1/0,L=H)=>{let{points:r,along:e}=M;if(r.length<2||!s(C))return null;let t=Math.cos(C[0]*Math.PI/180),i=C[1]*t,A=C[0],d=null;for(let p=1;p<r.length;p++){if(e[p]<H||e[p-1]>V)continue;let v=r[p-1][1]*t,x=r[p-1][0],u=r[p][1]*t-v,N=r[p][0]-x,d1=u*u+N*N,W=d1===0?0:Math.max(0,Math.min(1,((i-v)*u+(A-x)*N)/d1)),T=Math.hypot(i-v-W*u,A-x-W*N)*111320,I=Math.max(H,Math.min(V,e[p-1]+W*(e[p]-e[p-1])));(!d||(Math.abs(T-d.off)<=15?Math.abs(I-L)<Math.abs(d.along-L):T<d.off))&&(d={off:T,along:I})}return d},v5=(M,C)=>{let{points:H,along:V}=M;if(!H.length)return null;if(C<=0)return H[0];for(let L=1;L<H.length;L++)if(V[L]>=C){let r=V[L]-V[L-1],e=r?(C-V[L-1])/r:0;return[H[L-1][0]+e*(H[L][0]-H[L-1][0]),H[L-1][1]+e*(H[L][1]-H[L-1][1])]}return H[H.length-1]},y2=(M,C)=>{let{points:H,along:V}=M;if(H.length<2)return{done:[],ahead:H};let L=v5(M,C),r=H.filter((t,i)=>V[i]<C),e=H.filter((t,i)=>V[i]>C);return{done:[...r,L],ahead:[L,...e]}},B2=(M,C)=>{let H=0;return C.map(V=>{let L=f(V),r=L?$1(M,L,H):null;return r?(H=r.along,r.along):null})},P2=(M,C)=>{if(!s(C))return-1;let H=-1,V=1/0;return M.forEach((L,r)=>{let e=f(L);if(!e)return;let t=x1(C,e);t<V&&(V=t,H=r)}),V<=2e3?H:-1},T2=(M,C,H,V)=>{if(M.points.length<2||!s(V))return null;let L=H>=0?C[H]:null,r;if(L==null)r=$1(M,V);else{let e=C.slice(0,H).filter(d=>d!=null).at(-1),t=C.slice(H+1).find(d=>d!=null),i=Math.max(e??0,L-1500),A=Math.min(t??1/0,L+1500);r=$1(M,V,i,A,L)}return!r||r.off>200?null:r.along},_2=()=>{let M=null,C=null,H=-1;return{update(V,L,r){return(V!==M||H>=0&&L>=0&&L<H-3)&&(M=V,C=null,H=-1),r==null||((C==null||r>C)&&(C=r),L>H&&(H=L)),C},reset(){M=null,C=null,H=-1}}},R2=({stops:M,vehicle:C,hereIndex:H,mineIndex:V})=>{let L=M.map(f).filter(s),r=V>=0?f(M[V]):null;if(!s(C))return L;if(H<0)return[C,...r?[r]:L];let e=V>H?Math.min(V,H+12):H+6,t=M.slice(H,e+1).map(f).filter(s);return[C,...t.length?t:L]},F2=M=>{let C=(M||[]).filter(s);if(!C.length)return null;let H=1/0,V=-1/0,L=1/0,r=-1/0;for(let[e,t]of C)H=Math.min(H,e),V=Math.max(V,e),L=Math.min(L,t),r=Math.max(r,t);return[[L,H],[r,V]]},D2=(M,C,H=Date.now())=>{let V=Date.parse(M);return Number.isNaN(V)?null:Math.max(0,Math.round((H+C-V)/1e3))},E2=(M,C)=>{let H=Date.parse(M);return Number.isNaN(H)?0:H-C},$2=M=>{let C=new Map;return(H,V)=>{let L=`${H}|${V}`;if(C.has(L))return C.get(L);let r=null;if(H&&String(H).trim())try{r=M(String(H).trim())}catch{r=null}let e=r||V;return C.set(L,e),e}};var c="israel_transit",N2="israel-transit-dialog-closed",W2=`/${c}/brand/icon.png`,Z1={0:["#7b4fd1","#b39ddb"],2:["#1e6fbf","#64b5f6"],3:["#2f7d4f","#66bb6a"],5:["#a3581a","#ffb74d"],8:["#8a7320","#e6c84a"],715:["#4a6572","#90a4ae"]},N1=["#0277bd","#4fc3f7"];var W1=["#9c6200","#ffb300"],I1=M=>M!=null&&Z1[M]!=null,y=M=>I1(M)?`var(--it-mode-${M})`:"var(--it-mode-unknown)",I2=(M,C)=>(I1(M)?Z1[M]:N1)[C?1:0],t1=(M,C)=>I1(C)?S(M,`mode_${C}`):"",z2=(M,C=Date.now())=>{let H=Date.parse(M);return Number.isNaN(H)?null:Math.max(0,Math.floor((H-C)/6e4))},x5=M=>{if(!M)return!1;if(M.time_format==="12")return!0;if(M.time_format==="24")return!1;let C=M.time_format==="system"?void 0:M.language;return new Date("January 1, 2023 22:00:00").toLocaleString(C).includes("10")},Q=(M,C)=>{let H=new Date(M);if(Number.isNaN(H.getTime()))return"";let V=C?.locale;try{return new Intl.DateTimeFormat(V?.language||"he-IL",{hour:"2-digit",minute:"2-digit",hourCycle:x5(V)?"h12":"h23",timeZone:V?.time_zone==="server"?C?.config?.time_zone:void 0}).format(H)}catch{return H.toTimeString().slice(0,5)}},Z5={unknown_stop:"errorUnknownStop",unknown_command:"errorNotLoaded",search_failed:"errorIndex",lookup_failed:"errorIndex",3:"errorConnection"},i1=(M,C)=>{let H=C?.code??C?.error?.code,V=Z5[H];return V?S(M,V):S(M,"errorGeneric")},U2=(M,C,H={})=>{let V=new CustomEvent(C,{detail:H,bubbles:!0,composed:!0});return M.dispatchEvent(V),V},E=()=>window.matchMedia?.("(prefers-reduced-motion: reduce)").matches??!1,o1=M=>!!M?.themes?.darkMode;var s5=n1(Object.entries(Z1).map(([M,[C]])=>`--it-mode-${M}: ${C};`).join(`
    `)+`
    --it-mode-unknown: ${N1[0]};`),K=O`
  :host {
    ${s5}
    display: block;
  }

  .icon {
    flex: 0 0 auto;
    display: block;
  }

  /* Points the same way as the text in both directions. */
  :host(:dir(rtl)) .flip {
    transform: scaleX(-1);
  }

  .badge {
    flex: 0 0 auto;
    box-sizing: border-box;
    min-width: 44px;
    height: 28px;
    padding-inline: var(--ha-space-2, 8px);
    border-radius: var(--ha-border-radius-pill, 9999px);
    background: var(--it-badge-color, var(--it-mode-unknown));
    color: #fff;
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-bold, 700);
    line-height: 28px;
    text-align: center;
    white-space: nowrap;
    font-variant-numeric: tabular-nums;
    /* Line numbers stay left-to-right even inside an RTL layout. */
    direction: ltr;
    unicode-bidi: isolate;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    gap: var(--ha-space-1, 4px);
    white-space: nowrap;
  }

  .tag.timetable {
    color: var(--secondary-text-color);
  }

  .ltr {
    direction: ltr;
    unicode-bidi: isolate;
    font-variant-numeric: tabular-nums;
  }

  /* -- states: loading, empty, error, stale -- */

  .skeleton {
    display: flex;
    align-items: center;
    gap: var(--ha-space-4, 16px);
    min-height: 48px;
    padding: var(--ha-space-3, 12px) var(--ha-space-4, 16px);
    box-sizing: border-box;
    animation: fade-in 300ms ease-in;
  }

  .bone {
    border-radius: var(--ha-border-radius-sm, 4px);
    background: var(--ha-color-fill-neutral-quiet-resting, rgba(127, 127, 127, 0.14));
  }

  .bone.pill {
    width: 44px;
    height: 28px;
    border-radius: var(--ha-border-radius-pill, 9999px);
  }

  .bone.text {
    flex: 1 1 auto;
    height: 12px;
  }

  .bone.eta {
    width: 32px;
    height: 20px;
  }

  @keyframes fade-in {
    from {
      opacity: 0;
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .skeleton {
      animation: none;
    }
  }

  .empty {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--ha-space-2, 8px);
    max-width: 500px;
    margin-inline: auto;
    padding: var(--ha-space-6, 24px) var(--ha-space-4, 16px);
    text-align: center;
    color: var(--secondary-text-color);
  }

  .empty .icon {
    color: var(--secondary-text-color);
    opacity: 0.8;
  }

  .empty-title {
    margin: 0;
    font-size: var(--ha-font-size-l, 16px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
  }

  .empty-text {
    margin: 0;
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-normal, 1.6);
  }

  /* Home Assistant's alert, narrow variant: the colour of its kind at 12%
     behind it, an icon that says the same thing as the colour. */
  .alert {
    --it-alert: var(--info-color, #039be5);
    display: flex;
    align-items: flex-start;
    gap: var(--ha-space-2, 8px);
    padding: var(--ha-space-2, 8px) var(--ha-space-3, 12px);
    border-radius: var(--ha-border-radius-sm, 4px);
    background: rgba(127, 127, 127, 0.12);
    background: color-mix(in srgb, var(--it-alert) 12%, transparent);
    color: var(--primary-text-color);
    font-size: var(--ha-font-size-s, 12px);
    line-height: var(--ha-line-height-normal, 1.6);
  }

  .alert .icon {
    color: var(--it-alert);
  }

  .alert.error {
    --it-alert: var(--error-color, #db4437);
  }

  .alert.warning {
    --it-alert: var(--warning-color, #ffa600);
  }

  .alert.info {
    --it-alert: var(--info-color, #039be5);
  }
`,G2=O`
  ha-card {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    container-type: inline-size;
  }

  .header {
    display: flex;
    align-items: center;
    gap: var(--ha-space-3, 12px);
    width: 100%;
    min-height: 48px;
    padding: var(--ha-space-4, 16px) var(--ha-space-4, 16px) var(--ha-space-2, 8px);
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    box-sizing: border-box;
  }

  .header:focus-visible,
  .row:focus-visible {
    outline: 2px solid var(--ha-color-focus, var(--primary-color));
    outline-offset: -2px;
    border-radius: var(--ha-card-border-radius, 12px);
  }

  .titles {
    flex: 1 1 auto;
    min-width: 0;
  }

  .stop-name {
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .stop-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--ha-space-2, 8px);
    margin-block-start: var(--ha-space-1, 4px);
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .code {
    padding: 0 var(--ha-space-2, 8px);
    border-radius: var(--ha-border-radius-pill, 9999px);
    background: var(--ha-color-fill-neutral-quiet-resting, rgba(127, 127, 127, 0.14));
    line-height: 20px;
  }

  .header .info {
    color: var(--secondary-text-color);
  }

  .notice {
    padding: 0 var(--ha-space-4, 16px) var(--ha-space-2, 8px);
  }

  .rows {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    overflow-y: auto;
    padding-block-end: var(--ha-space-2, 8px);
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--ha-space-3, 12px);
    width: 100%;
    min-height: 56px;
    padding: var(--ha-space-2, 8px) var(--ha-space-4, 16px);
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    box-sizing: border-box;
    transition: background-color var(--ha-animation-duration-fast, 150ms);
  }

  .row + .row {
    box-shadow: inset 0 1px 0 var(--divider-color, rgba(127, 127, 127, 0.2));
  }

  .row:hover {
    background: var(--ha-color-fill-neutral-quiet-hover, rgba(127, 127, 127, 0.08));
  }

  .row:active {
    background: var(--ha-color-fill-neutral-quiet-active, rgba(127, 127, 127, 0.14));
  }

  .mode {
    color: var(--secondary-text-color);
  }

  .row-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .destination {
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sub {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0 var(--ha-space-1, 4px);
    margin-block-start: var(--ha-space-1, 4px);
    font-size: var(--ha-font-size-s, 12px);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--secondary-text-color);
  }

  .eta {
    flex: 0 0 auto;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    min-width: 48px;
    text-align: end;
  }

  .eta-main {
    display: flex;
    align-items: baseline;
    gap: var(--ha-space-1, 4px);
  }

  .eta-value {
    font-size: var(--ha-font-size-xl, 20px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }

  .eta-unit {
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .eta-now .eta-value {
    font-size: var(--ha-font-size-l, 16px);
    color: var(--success-color, #43a047);
  }

  .eta-clock {
    font-size: var(--ha-font-size-l, 16px);
  }

  .eta-extra {
    display: flex;
    align-items: center;
    gap: var(--ha-space-1, 4px);
    margin-block-start: 2px;
    font-size: var(--ha-font-size-xs, 10px);
    color: var(--secondary-text-color);
  }

  .live {
    color: var(--success-color, #43a047);
  }

  .delay {
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--ha-color-text-warning, var(--warning-color, #ffa600));
  }

  .chevron {
    color: var(--secondary-text-color);
    margin-inline-start: calc(-1 * var(--ha-space-1, 4px));
  }

  /* Times that stopped updating: still the last real answer, so they stay,
     but greyed until a fresh one arrives. */
  .rows.stale .eta,
  .rows.stale .live {
    opacity: 0.55;
  }

  /* Genuinely narrow dashboard columns: drop to the essentials. A
     full-width card on a small phone is ~327px, and should keep everything. */
  @container (max-width: 290px) {
    .header,
    .row {
      padding-inline: var(--ha-space-3, 12px);
    }
    .row {
      gap: var(--ha-space-2, 8px);
    }
    .sub .operator,
    .sub .operator + .sep,
    .mode,
    .chevron {
      display: none;
    }
    .eta-value {
      font-size: var(--ha-font-size-l, 16px);
    }
  }
`;var u5=3e4,S5=1e4,c5=6e4,b={max_arrivals:6,max_lines:0,order:"time",show_header:!0,show_city:!0,show_stop_code:!0,show_destination:!0,show_operator:!0,show_mode_icon:!1,show_realtime_tag:!0,show_platform:!0,show_delay:!0,show_clock:!1,show_map:!0},q=class extends Z{constructor(){super();l(this,"_onReconnect",()=>this._refresh());this._data=null,this._error=null,this._tick=0,this._stopDialog=!1,this._routeDialog=null}set hass(H){let V=!this._hass;this._hass=H,H?.connection!==this._connection&&this._watch(H?.connection);let L=[H?.language,H?.locale?.language,H?.locale?.time_format,H?.locale?.time_zone,o1(H)].join("|");L!==this._look&&(this._look=L,this.requestUpdate()),V&&this._refresh()}get hass(){return this._hass}static getConfigElement(){return document.createElement("israel-transit-card-editor")}static getStubConfig(H){return{stop_code:Object.values(H?.states||{}).find(L=>L.attributes?.stop_code)?.attributes.stop_code??null,max_arrivals:b.max_arrivals}}setConfig(H){if(!H||typeof H!="object")throw new Error(S(this.hass,"errorNoStop"));this._config={...b,...H},this._data=null,this._error=null,this._refresh()}getCardSize(){return(this._config?.max_arrivals??b.max_arrivals)+2}getGridOptions(){let H=Math.min(this._config?.max_arrivals??b.max_arrivals,8),V=this._config?.show_header===!1?1:2;return{rows:H+V,columns:12,min_rows:3,min_columns:6}}connectedCallback(){super.connectedCallback(),this._startTimers(),this._onVisibility=()=>{document.visibilityState==="visible"?(this._startTimers(),this._refresh()):this._stopTimers()},document.addEventListener("visibilitychange",this._onVisibility),this._connection?.addEventListener("ready",this._onReconnect),this._refresh()}disconnectedCallback(){super.disconnectedCallback(),this._stopTimers(),document.removeEventListener("visibilitychange",this._onVisibility),this._connection?.removeEventListener("ready",this._onReconnect)}_watch(H){this._connection?.removeEventListener("ready",this._onReconnect),this._connection=H,this.isConnected&&H?.addEventListener("ready",this._onReconnect)}_startTimers(){this._stopTimers(),document.visibilityState!=="hidden"&&(this._refreshTimer=setInterval(()=>this._refresh(),u5),this._tickTimer=setInterval(()=>{this._tick=Date.now()},S5))}_stopTimers(){clearInterval(this._refreshTimer),clearInterval(this._tickTimer),this._refreshTimer=void 0,this._tickTimer=void 0}async _refresh(){if(!this.hass||!this._config?.stop_code)return;let H=Number(this._config.stop_code);try{let V=await this.hass.callWS({type:`${c}/stop`,stop_code:H,rail_destination:this._config.rail_destination||null});if(H!==Number(this._config?.stop_code))return;this._clockOffset=E2(V.server_time,Date.now()),this._data=V,this._error=null,this._followVehicle()}catch(V){if(H!==Number(this._config?.stop_code))return;this._error=i1(this.hass,V)}}_followVehicle(){let H=this._routeDialog;if(!H)return;let V=this._data?.arrivals||[],L=H.vehicle_ref?V.find(r=>r.vehicle_ref===H.vehicle_ref):V.find(r=>r.line_ref===H.line_ref);L&&(this._routeDialog=L)}_t(H){return S(this.hass,H)}get _arrivals(){let H=this._config,V=Date.now()-c5,L=(this._data?.arrivals||[]).filter(i=>!(Date.parse(i.eta)<V)),r=(H.lines||[]).map(String),e=r.length?L.filter(i=>r.includes(String(i.line_name))):L;H.order==="lines"&&r.length&&(e=[...e].sort((i,A)=>r.indexOf(String(i.line_name))-r.indexOf(String(A.line_name))));let t=Number(H.max_lines)||0;if(t>0){let i=new Set;e=e.filter(A=>{let d=String(A.line_name);return i.has(d)?!0:i.size>=t?!1:(i.add(d),!0)})}return e.slice(0,H.max_arrivals??b.max_arrivals)}render(){if(!this._config)return a;if(!this._config.stop_code)return o`<ha-card>
        ${this._renderEmpty(m.busStop,this._t("editorNoStop"),this._t("editorSearch"))}
      </ha-card>`;let H=this._data?.stop;this._tick;let V=this._data?this._arrivals:[],L=!!(this._error&&this._data);return o`
      <ha-card>
        ${this._config.show_header===!1?a:this._renderHeader(H)}
        ${L?o`<div class="notice">
              <div class="alert warning" role="status">
                ${n(m.offline,{size:18})}<span>${this._t("staleData")}</span>
              </div>
            </div>`:a}
        <div
          class="rows ${L?"stale":""}"
          aria-busy=${!this._data&&!this._error?"true":"false"}
        >
          ${this._data?V.length===0?this._renderEmpty(m.empty,this._t("emptyTitle"),this._emptyMessage()):V.map(r=>this._renderRow(r)):this._error?o`<div class="notice">
                  <div class="alert error" role="alert">
                    ${n(m.alert,{size:18})}<span>${this._error}</span>
                  </div>
                </div>`:this._renderSkeleton()}
        </div>
        ${this._renderDialogs(H)}
      </ha-card>
    `}_renderSkeleton(){let H=Math.min(this._config.max_arrivals??3,3);return o`<div role="progressbar" aria-label=${this._t("loading")}>
      ${Array.from({length:H},()=>o`<div class="skeleton" aria-hidden="true">
          <span class="bone pill"></span><span class="bone text"></span
          ><span class="bone eta"></span>
        </div>`)}
    </div>`}_renderEmpty(H,V,L){return o`<div class="empty">
      ${n(H,{size:40})}
      <p class="empty-title">${V}</p>
      ${L?o`<p class="empty-text">${L}</p>`:a}
    </div>`}_emptyMessage(){return this._config.lines?.length?this._t("noArrivals"):this._data.realtime_error&&!this._data.routes?.length?this._t("noData"):this._data.realtime_error?this._t("noRealtime"):this._t("noArrivals")}_renderHeader(H){let V=this._config.title||H?.name||this._t("loading"),L=this._config.show_city!==!1&&H?.city,r=this._config.show_stop_code!==!1&&H?.code;return o`
      <button
        class="header"
        part="header"
        @click=${e=>this._open("_stopDialog",!0,e)}
        aria-label=${`${V}. ${this._t("stopDetails")}`}
      >
        <div class="titles">
          <div class="stop-name">${V}</div>
          ${L||r?o`<div class="stop-meta">
                ${L?o`<span>${H.city}</span>`:a}
                ${r?o`<span class="code ltr">${H.code}</span>`:a}
              </div>`:a}
        </div>
        ${n(m.info,{size:24,cls:"icon info"})}
      </button>
    `}_open(H,V,L){this._opener=L?.currentTarget??null,this[H]=V}_renderRow(H){let V=this._config,L=z2(H.eta),r=L===null||L>59,e=Q(H.eta,this.hass),t=H.destination||H.line_name,i=r?e:L===0?this._t("now"):`${L} ${this._t("minutesLong")}`;return o`
      <button
        class="row"
        @click=${A=>this._open("_routeDialog",H,A)}
        aria-label=${[`${t1(this.hass,H.route_type)||this._t("lineDetails")} ${H.line_name}`,t,i,H.is_realtime?this._t("live"):this._t("scheduled")].join(", ")}
      >
        ${V.show_mode_icon?n(G(H.route_type),{cls:"icon mode"}):a}
        <div
          class="badge"
          style=${`--it-badge-color:${y(H.route_type)}`}
        >
          ${H.line_name}
        </div>
        <div class="row-body">
          ${V.show_destination!==!1?o`<div class="destination">${t}</div>`:a}
          ${this._renderSub(H)}
        </div>
        <div class="eta ${L===0?"eta-now":""}" aria-hidden="true">
          <div class="eta-main">
            ${r?o`<span class="eta-value eta-clock ltr">${e}</span>`:L===0?o`<span class="eta-value">${this._t("now")}</span>`:o`<span class="eta-value">${L}</span>
                    <span class="eta-unit">${this._t("minutes")}</span>`}
          </div>
          ${this._renderEtaExtra(H,r,e)}
        </div>
        ${n(m.chevron,{size:20,cls:"icon chevron flip"})}
      </button>
    `}_renderEtaExtra(H,V,L){let r=this._config,e=[H.is_realtime?n(m.live,{size:12,cls:"icon live"}):a,r.show_clock&&!V?o`<span class="ltr">${L}</span>`:a,r.show_delay!==!1&&H.delay_minutes?o`<span class="delay ltr">+${H.delay_minutes}</span>`:a].filter(t=>t!==a);return e.length?o`<div class="eta-extra">${e}</div>`:a}_renderSub(H){let V=this._config,L=[V.show_operator!==!1&&H.operator?o`<span class="operator">${H.operator}</span>`:a,V.show_realtime_tag!==!1&&!H.is_realtime?o`<span class="tag timetable"
            >${n(m.timetable,{size:14})}${this._t("scheduled")}</span
          >`:a,V.show_platform!==!1&&H.platform?o`<span>${this._t("platform")} ${H.platform}</span>`:a].filter(r=>r!==a);return L.length?o`<div class="sub">
      ${L.map((r,e)=>e?o`<span class="sep" aria-hidden="true">·</span>${r}`:r)}
    </div>`:a}_renderDialogs(H){return o`
      ${this._stopDialog?o`<israel-transit-stop-dialog
            .hass=${this.hass}
            .stop=${H}
            .opener=${this._opener}
            .open=${!0}
            @israel-transit-dialog-closed=${()=>this._stopDialog=!1}
          ></israel-transit-stop-dialog>`:a}
      ${this._routeDialog?o`<israel-transit-route-dialog
            .hass=${this.hass}
            .arrival=${this._routeDialog}
            .stopCode=${H?.code??this._config.stop_code}
            .showMap=${this._config.show_map!==!1}
            .clockOffset=${this._clockOffset??0}
            .opener=${this._opener}
            .open=${!0}
            @israel-transit-dialog-closed=${()=>this._routeDialog=null}
          ></israel-transit-route-dialog>`:a}
    `}};l(q,"properties",{_config:{state:!0},_data:{state:!0},_error:{state:!0},_tick:{state:!0},_stopDialog:{state:!0},_routeDialog:{state:!0}}),l(q,"styles",[K,G2]);var h5="(min-width: 871px) and (min-height: 501px)",O5=400,f5=8,g5=.5,k5=()=>{let M=document.activeElement;for(;M?.shadowRoot?.activeElement;)M=M.shadowRoot.activeElement;return M},j=class extends Z{constructor(){super(),this.open=!1,this.heading="",this.subheading="",this.closeLabel="Close",this._sheet=!1,this._scrolled=!1}get _dialog(){return this.renderRoot.querySelector("dialog")}updated(C){C.has("open")&&(this.open?this._show():C.get("open")&&this.close())}disconnectedCallback(){super.disconnectedCallback(),clearTimeout(this._closeTimer),this._dialog?.close()}_show(){let C=this._dialog;!C||C.open||(this._returnTo=this.opener??k5(),this._sheet=!window.matchMedia(h5).matches,this._closing=!1,C.showModal(),requestAnimationFrame(()=>C.classList.add("shown")))}close(){let C=this._dialog;if(!C?.open||this._closing)return;if(this._closing=!0,C.classList.remove("shown","dragging"),C.style.removeProperty("--it-drag"),E()){C.close();return}let H=()=>{clearTimeout(this._closeTimer),C.removeEventListener("transitionend",V),C.open&&C.close()},V=L=>{L.target===C&&H()};C.addEventListener("transitionend",V),this._closeTimer=setTimeout(H,O5)}_onCancel(C){C.preventDefault(),this.close()}_onClose(){clearTimeout(this._closeTimer),this._closing=!1;let C=this._dialog;C?.classList.remove("shown","dragging"),C?.style.removeProperty("--it-drag"),this.open=!1;let H=this._returnTo;this._returnTo=void 0,H?.isConnected&&H.focus?.({preventScroll:!0}),this.dispatchEvent(new CustomEvent("closed"))}_onKeydown(C){C.stopPropagation()}_onPointerDown(C){this._downOnBackdrop=C.target===this._dialog}_onClick(C){this._downOnBackdrop&&C.target===this._dialog&&this.close(),this._downOnBackdrop=!1}_onScroll(C){this._scrolled=C.target.scrollTop>0}_onDragStart(C){!this._sheet||C.button>0||C.target.closest?.("button, a, input, select, textarea")||(this._drag={id:C.pointerId,y:C.clientY,t:C.timeStamp,active:!1})}_onDragMove(C){let H=this._drag;if(!H||C.pointerId!==H.id)return;let V=C.clientY-H.y;if(!H.active){if(Math.abs(V)<f5)return;H.active=!0;try{C.currentTarget.setPointerCapture?.(C.pointerId)}catch{}this._dialog.classList.add("dragging")}H.dy=Math.max(0,V),H.last=C.timeStamp,this._dialog.style.setProperty("--it-drag",`${H.dy}px`)}_onDragEnd(C){let H=this._drag;if(this._drag=void 0,!H?.active||C.pointerId!==H.id)return;let V=this._dialog;V.classList.remove("dragging");let L=Math.max(1,(H.last??C.timeStamp)-H.t);H.dy/L>g5||H.dy>V.offsetHeight/2?this.close():V.style.removeProperty("--it-drag")}render(){let C={down:H=>this._onDragStart(H),move:H=>this._onDragMove(H),up:H=>this._onDragEnd(H)};return o`
      <dialog
        class=${this._sheet?"sheet":""}
        aria-labelledby="title"
        @cancel=${this._onCancel}
        @close=${this._onClose}
        @keydown=${this._onKeydown}
        @pointerdown=${this._onPointerDown}
        @click=${this._onClick}
      >
        ${this._sheet?o`<div
              class="handle"
              aria-hidden="true"
              @pointerdown=${C.down}
              @pointermove=${C.move}
              @pointerup=${C.up}
              @pointercancel=${C.up}
            ></div>`:a}
        <header
          class=${this._scrolled?"scrolled":""}
          @pointerdown=${C.down}
          @pointermove=${C.move}
          @pointerup=${C.up}
          @pointercancel=${C.up}
        >
          <button
            class="close"
            aria-label=${this.closeLabel}
            title=${this.closeLabel}
            @click=${()=>this.close()}
          >
            ${n(m.close,{size:24})}
          </button>
          <div class="titles">
            <h2 id="title">${this.heading}</h2>
            ${this.subheading?o`<div class="subheading">${this.subheading}</div>`:a}
          </div>
          <slot name="actions"></slot>
        </header>
        <div class="body" @scroll=${this._onScroll}>
          ${this.open?o`<slot></slot>`:a}
        </div>
      </dialog>
    `}};l(j,"properties",{open:{type:Boolean},heading:{},subheading:{},closeLabel:{attribute:!1},opener:{attribute:!1},_sheet:{state:!0},_scrolled:{state:!0}}),l(j,"styles",O`
    dialog {
      --it-dialog-duration: 200ms;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      width: min(580px, calc(100vw - 32px));
      max-width: none;
      max-height: calc(100vh - 80px);
      max-height: calc(100dvh - 80px);
      margin: auto;
      padding: 0;
      border: none;
      border-radius: var(--ha-border-radius-3xl, 24px);
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      box-shadow: var(--ha-box-shadow-l, 0 6px 12px -3px rgba(0, 0, 0, 0.12), 0 16px 32px -6px rgba(0, 0, 0, 0.2));
      overflow: hidden;
      opacity: 0;
      transform: scale(0.96);
      transition:
        opacity var(--it-dialog-duration) ease-out,
        transform var(--it-dialog-duration) ease-out;
    }

    dialog:not([open]) {
      display: none;
    }

    dialog.shown {
      opacity: 1;
      transform: none;
    }

    dialog::backdrop {
      background: rgba(0, 0, 0, 0.32);
      opacity: 0;
      transition: opacity var(--it-dialog-duration) ease-out;
    }

    dialog.shown::backdrop {
      opacity: 1;
    }

    dialog.sheet {
      --it-dialog-duration: 300ms;
      width: 100%;
      max-height: 90vh;
      max-height: 90dvh;
      margin: auto 0 0;
      border-end-start-radius: 0;
      border-end-end-radius: 0;
      border-start-start-radius: var(--ha-border-radius-2xl, 20px);
      border-start-end-radius: var(--ha-border-radius-2xl, 20px);
      padding-block-end: env(safe-area-inset-bottom);
      opacity: 1;
      transform: translateY(100%);
    }

    dialog.sheet.shown {
      transform: translateY(var(--it-drag, 0px));
    }

    dialog.dragging {
      transition: none;
    }

    @media (prefers-reduced-motion: reduce) {
      dialog,
      dialog::backdrop {
        transition: none;
      }
    }

    .handle {
      flex: 0 0 auto;
      display: flex;
      justify-content: center;
      padding-block: var(--ha-space-2, 8px) 0;
      touch-action: none;
      cursor: grab;
    }

    .handle::before {
      content: "";
      width: 32px;
      height: 4px;
      border-radius: var(--ha-border-radius-pill, 9999px);
      background: var(--ha-color-border-neutral-normal, rgba(127, 127, 127, 0.5));
    }

    header {
      flex: 0 0 auto;
      display: flex;
      align-items: flex-start;
      gap: var(--ha-space-1, 4px);
      min-height: 48px;
      padding: var(--ha-space-2, 8px) var(--ha-space-4, 16px) var(--ha-space-2, 8px) var(--ha-space-2, 8px);
      padding-inline: var(--ha-space-2, 8px) var(--ha-space-6, 24px);
      border-block-end: var(--ha-border-width-sm, 1px) solid transparent;
      transition: border-color var(--ha-animation-duration-fast, 150ms);
    }

    .sheet header {
      touch-action: none;
    }

    header.scrolled {
      border-block-end-color: var(--divider-color, rgba(127, 127, 127, 0.2));
    }

    .close {
      flex: 0 0 auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      padding: 0;
      border: none;
      border-radius: 50%;
      background: none;
      color: var(--primary-text-color);
      cursor: pointer;
    }

    .close:hover {
      background: var(--ha-color-fill-neutral-quiet-hover, rgba(127, 127, 127, 0.12));
    }

    .close:focus-visible {
      outline: 2px solid var(--ha-color-focus, var(--primary-color));
      outline-offset: 2px;
    }

    .titles {
      flex: 1 1 auto;
      min-width: 0;
      padding-block: 12px var(--ha-space-1, 4px);
    }

    h2 {
      margin: 0;
      font-size: var(--ha-font-size-xl, 20px);
      font-weight: var(--ha-font-weight-medium, 500);
      line-height: var(--ha-line-height-condensed, 1.2);
      overflow-wrap: anywhere;
    }

    .subheading {
      margin-block-start: var(--ha-space-1, 4px);
      font-size: var(--ha-font-size-m, 14px);
      line-height: var(--ha-line-height-condensed, 1.2);
      color: var(--secondary-text-color);
    }

    .body {
      flex: 1 1 auto;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      padding: 0 var(--ha-space-6, 24px) var(--ha-space-6, 24px);
    }

    .sheet .body {
      padding-inline: var(--ha-space-4, 16px);
    }
  `);var b5=120,w5=15e3,y5=40,B=new Map,Q2=null,B5=M=>{let C=B.get(M);return C&&(B.delete(M),B.set(M,C)),C},P5=(M,C)=>{for(C.index!==Q2&&(B.clear(),Q2=C.index),B.set(M,C);B.size>y5;)B.delete(B.keys().next().value)},T5=M=>Array.isArray(M)?{stops:M,shape:null,index:null}:{stops:M?.stops??[],shape:M?.shape??null,index:M?.index??null},_5=O`
  .list {
    display: flex;
    flex-direction: column;
  }

  .item {
    display: flex;
    align-items: center;
    gap: var(--ha-space-4, 16px);
    min-height: 56px;
    padding-block: var(--ha-space-2, 8px);
    box-sizing: border-box;
  }

  .item + .item {
    box-shadow: inset 0 1px 0 var(--divider-color, rgba(127, 127, 127, 0.2));
  }

  .item-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .item-title {
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .item-sub {
    margin-block-start: var(--ha-space-1, 4px);
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .tag {
    font-size: var(--ha-font-size-s, 12px);
  }

  israel-transit-map {
    height: 260px;
    margin-block-end: var(--ha-space-3, 12px);
  }

  /* A bottom sheet on a phone has far less room than a desktop dialog. */
  @media (max-height: 700px) {
    israel-transit-map {
      height: 200px;
    }
  }

  /* -- the status of the vehicle, under the map -- */

  .status {
    display: flex;
    align-items: center;
    gap: var(--ha-space-3, 12px);
    margin-block-end: var(--ha-space-3, 12px);
    padding: var(--ha-space-3, 12px);
    border-radius: var(--ha-border-radius-lg, 12px);
    background: var(--ha-color-fill-neutral-quiet-resting, rgba(127, 127, 127, 0.1));
  }

  .status-icon {
    flex: 0 0 auto;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: var(--it-badge-color, var(--it-mode-unknown));
    color: #fff;
  }

  .status-icon.off {
    background: var(--ha-color-fill-neutral-normal-resting, rgba(127, 127, 127, 0.3));
    color: var(--secondary-text-color);
  }

  .status-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .status-title {
    font-size: var(--ha-font-size-m, 14px);
    font-weight: var(--ha-font-weight-medium, 500);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
  }

  .status-sub {
    display: flex;
    flex-wrap: wrap;
    gap: 0 var(--ha-space-2, 8px);
    margin-block-start: var(--ha-space-1, 4px);
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .status-sub .stale {
    color: var(--ha-color-text-warning, var(--warning-color, #ffa600));
  }

  .approx {
    margin-block-end: var(--ha-space-3, 12px);
  }

  /* -- the stop timeline -- */

  .timeline {
    display: flex;
    flex-direction: column;
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .stop {
    display: grid;
    grid-template-columns: 28px 1fr auto;
    align-items: center;
    gap: var(--ha-space-3, 12px);
    width: 100%;
    min-height: 48px;
    padding: var(--ha-space-1, 4px) 0;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    cursor: pointer;
    box-sizing: border-box;
  }

  .stop:disabled {
    cursor: default;
  }

  .stop:not(:disabled):hover {
    background: var(--ha-color-fill-neutral-quiet-hover, rgba(127, 127, 127, 0.08));
  }

  .stop:focus-visible {
    outline: 2px solid var(--ha-color-focus, var(--primary-color));
    outline-offset: -2px;
    border-radius: var(--ha-border-radius-md, 8px);
  }

  .track {
    position: relative;
    align-self: stretch;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  /* The line between stops, in the colour of the line. */
  .track::before {
    content: "";
    position: absolute;
    inset-block: -4px;
    width: 4px;
    border-radius: 2px;
    background: var(--it-badge-color, var(--it-mode-unknown));
  }

  li:first-child .track::before {
    inset-block-start: 50%;
  }

  li:last-child .track::before {
    inset-block-end: 50%;
  }

  .node {
    position: relative;
    box-sizing: border-box;
    width: 12px;
    height: 12px;
    border: 3px solid var(--it-badge-color, var(--it-mode-unknown));
    border-radius: 50%;
    background: var(--card-background-color, #fff);
  }

  .done .track::before,
  .done .node {
    opacity: 0.35;
  }

  .done .stop-title,
  .done .time {
    color: var(--secondary-text-color);
  }

  .here .node,
  .mine .node {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    border-width: 0;
    background: var(--it-badge-color, var(--it-mode-unknown));
    color: #fff;
  }

  .mine .node {
    background: var(--it-mine);
  }

  .stop-title {
    font-size: var(--ha-font-size-m, 14px);
    line-height: var(--ha-line-height-condensed, 1.2);
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .here .stop-title,
  .mine .stop-title {
    font-weight: var(--ha-font-weight-bold, 700);
  }

  .stop-sub {
    margin-block-start: 2px;
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
  }

  .stop-sub .mine-label {
    font-weight: var(--ha-font-weight-medium, 500);
    color: var(--primary-text-color);
  }

  .time {
    font-size: var(--ha-font-size-s, 12px);
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
  }
`,P=class extends Z{constructor(){super(),this.open=!1,this._loading=!1,this._error=null}set hass(C){this._hass=C;let H=[C?.language,C?.locale?.language,C?.locale?.time_format,o1(C)].join("|");H!==this._look&&(this._look=H,this.requestUpdate())}get hass(){return this._hass}_t(C,H){return S(this.hass,C,H)}_closed(){this.open=!1,this.dispatchEvent(new CustomEvent(N2))}_renderDialog(C,H,V){return o`<israel-transit-dialog
      .heading=${C}
      .subheading=${H}
      .closeLabel=${this._t("close")}
      .opener=${this.opener}
      .open=${this.open}
      @closed=${this._closed}
    >
      ${V}
    </israel-transit-dialog>`}_renderState(C,H){return this._loading?o`<div role="progressbar" aria-label=${this._t("loading")} aria-busy="true">
        ${[0,1,2].map(()=>o`<div class="skeleton" aria-hidden="true">
            <span class="bone pill"></span><span class="bone text"></span>
          </div>`)}
      </div>`:this._error?o`<div class="alert error" role="alert">
        ${n(m.alert,{size:18})}<span>${this._error}</span>
      </div>`:C.length?null:o`<div class="empty">
        ${n(m.empty,{size:40})}
        <p class="empty-title">${this._t("emptyTitle")}</p>
        <p class="empty-text">${this._t(H)}</p>
      </div>`}};l(P,"properties",{open:{type:Boolean},opener:{attribute:!1},_loading:{state:!0},_error:{state:!0}}),l(P,"styles",[K,_5]);var a1=class extends P{constructor(){super(),this._routes=[]}updated(C){C.has("open")&&this.open&&this._load()}async _load(){if(!(!this.hass||!this.stop)){this._loading=!0,this._error=null;try{this._routes=await this.hass.callWS({type:`${c}/stop_routes`,stop_code:this.stop.code})}catch(C){this._error=i1(this.hass,C)}finally{this._loading=!1}}}render(){let C=this.stop||{},H=this._renderState(this._routes,"noLines");return this._renderDialog(C.name||this._t("stopDetails"),[C.city,C.code].filter(Boolean).join(" \xB7 "),H??o`<div class="list" role="list" aria-label=${this._t("allLines")}>
          ${this._routes.map(V=>o`
              <div class="item" role="listitem">
                <div class="badge" style=${`--it-badge-color:${y(V.route_type)}`}>
                  ${V.line_name}
                </div>
                <div class="item-body">
                  <div class="item-title">${V.destination}</div>
                  <div class="item-sub">
                    ${[V.operator,t1(this.hass,V.route_type)].filter(Boolean).join(" \xB7 ")}
                  </div>
                </div>
                ${V.has_realtime?a:o`<span class="tag timetable"
                      >${n(m.timetable,{size:14})}${this._t("scheduled")}</span
                    >`}
              </div>
            `)}
        </div>`)}};l(a1,"properties",{...P.properties,stop:{attribute:!1},_routes:{state:!0}});var A1=class extends P{constructor(){super(),this.showMap=!0,this.clockOffset=0,this._route={stops:[],shape:null,index:null},this._now=Date.now(),this._progress=_2(),this._request=0}connectedCallback(){super.connectedCallback(),this._ageTimer=setInterval(()=>this._now=Date.now(),w5)}disconnectedCallback(){super.disconnectedCallback(),clearInterval(this._ageTimer),this._progress.reset(),this._request+=1}willUpdate(C){if(C.has("arrival")||C.has("open")){let H=this._routeKey;this.open&&H!==this._loadedKey&&this._load(H)}C.has("arrival")&&(this._now=Date.now())}get _routeKey(){let C=this.arrival||{};return C.line_ref?`${C.line_ref}|${C.departed??""}`:""}async _load(C){this._loadedKey=C,this._error=null;let H=this.arrival||{};if(!this.hass||!H.line_ref){this._route={stops:[],shape:null,index:null},this._error=this._t("noRouteStops");return}let V=B5(C);if(V){this._route=V;return}let L=++this._request;this._loading=!this._route.stops.length;try{let r=T5(await this.hass.callWS({type:`${c}/route_stops`,line_ref:H.line_ref,departed:H.departed||null}));if(L!==this._request)return;P5(C,r),this._route=r}catch(r){if(L!==this._request)return;this._error=i1(this.hass,r)}finally{L===this._request&&(this._loading=!1)}}get _vehiclePoint(){let{vehicle_lat:C,vehicle_lon:H}=this.arrival||{},V=C!=null&&H!=null?[Number(C),Number(H)]:null;return s(V)?V:null}_picture(){let C=this.arrival||{},H=this._route.stops||[],V=o1(this.hass),L=this._vehiclePoint,r=P2(H,L),e=this.stopCode==null?null:Number(this.stopCode),t=e==null?-1:H.findIndex(h=>Number(h.code)===e),i=(this._route.shape||[]).filter(s),A=i.length<2,d=w2(A?H.map(f).filter(s):i),p=B2(d,H),v=T2(d,p,r,L),x=`${C.line_ref}|${C.vehicle_ref??""}`,u=this._progress.update(x,r,v),{done:N,ahead:d1}=u!=null&&v!=null?y2(d,u):{done:[],ahead:d.points},W=h=>u!=null&&p[h]!=null?p[h]<u-30:h<r,T=L?D2(C.vehicle_seen,this.clockOffset??0,this._now):null,I=T!=null&&T>b5,c1=h=>H[h]?.name??"";return{view:{dark:V,dashed:A,color:I2(C.route_type,V),mineColor:W1[V?1:0],line:d.points,done:N,ahead:d1,stops:H.map((h,h1)=>({point:f(h),name:h.name,done:W(h1)})).filter((h,h1)=>s(h.point)&&h1!==t),mine:t>=0&&s(f(H[t]))?{point:f(H[t]),name:c1(t),label:`${this._t("myStop")}: ${c1(t)}`}:null,vehicle:L?{point:L,icon:G(C.route_type),lineName:C.line_name,stale:I,label:this._t(I?"vehicleStale":"vehicleOf",{line:C.line_name??""})}:null,bounds:F2(R2({stops:H,vehicle:L,hereIndex:r,mineIndex:t})),fitKey:`${x}|${r}|${t}|${H.length}|${i.length}`,subject:x},here:r,mine:t,passed:W,age:T,stale:I,dashed:A,vehicle:L}}_strings(){let C=H=>this._t(H);return{unavailable:C("mapUnavailable"),unsupported:C("mapUnsupported"),failed:C("mapFailed"),vendor:C("mapVendor"),retry:C("retry"),reload:C("reload"),recenter:C("recenter"),maplibre:{"NavigationControl.ZoomIn":C("zoomIn"),"NavigationControl.ZoomOut":C("zoomOut"),"AttributionControl.ToggleAttribution":C("attribution"),"Map.Title":C("mapLabel")}}}_relative(C){if(C==null)return"";let H=Math.round(C/60);return H?`+${H} ${this._t("minutes")}`:""}_focusStop(C){this.renderRoot.querySelector("israel-transit-map")?.focusOn(f(C))}render(){let C=this.arrival||{},H=this._route.stops||[],V=this._picture(),L=[t1(this.hass,C.route_type),C.line_name].filter(Boolean).join(" "),r=this._renderState(H,"noRouteStops"),e=this.showMap&&H.length>0;return this._renderDialog(`${L}${C.destination?` \xB7 ${C.destination}`:""}`,[C.operator,this._t("routeStops")].filter(Boolean).join(" \xB7 "),o`
        <div style=${`--it-badge-color:${y(C.route_type)};--it-mine:${W1[0]}`}>
          ${e?o`<israel-transit-map
                .view=${V.view}
                .strings=${this._strings()}
              ></israel-transit-map>`:a}
          ${H.length?this._renderStatus(C,H,V):a}
          ${e&&V.dashed&&H.length>1?o`<div class="alert info approx" role="note">
                ${n(m.map,{size:18})}<span>${this._t("approximateRoute")}</span>
              </div>`:a}
          ${r??this._renderTimeline(H,V,e)}
        </div>
      `)}_renderStatus(C,H,{here:V,mine:L,age:r,stale:e,vehicle:t}){let i;t&&V>=0?i=V===L?this._t("atYourStop"):this._t("nearStop",{stop:H[V].name}):t?i=this._t("awayFromRoute"):C.is_realtime?i=this._t("noVehicleLocation"):i=this._t("scheduled");let A=[];if(t&&V>=0&&L>V){let d=L-V;A.push(d===1?this._t("stopsToGoOne"):this._t("stopsToGo",{n:d}))}return C.eta&&A.push(this._t("arrivesAt",{time:Q(C.eta,this.hass)})),!t&&C.departed&&A.push(`${this._t("departedAt")}${Q(C.departed,this.hass)}`),o`<div class="status" role="status">
      <div class="status-icon ${t?"":"off"}">
        ${n(t?G(C.route_type):m.noPosition,{size:22})}
      </div>
      <div class="status-body">
        <div class="status-title">${i}</div>
        ${A.length||e?o`<div class="status-sub">
              ${A.map(d=>o`<span>${d}</span>`)}
              ${e?o`<span class="stale"
                    >${r<60?this._t("positionAgeSeconds"):this._t("positionAge",{n:Math.floor(r/60)})}</span
                  >`:a}
            </div>`:a}
      </div>
    </div>`}_renderTimeline(C,{here:H,mine:V,passed:L},r){return o`<ol class="timeline" aria-label=${this._t("routeStops")}>
      ${C.map((e,t)=>{let i=t===H,A=t===V,d=s(f(e)),p=[L(t)&&!i?"done":"",i?"here":"",A?"mine":""].join(" ");return o`<li class=${p}>
          <button
            class="stop"
            ?disabled=${!r||!d}
            title=${r&&d?this._t("showOnMap"):""}
            @click=${()=>this._focusStop(e)}
          >
            <div class="track">
              <div class="node">
                ${i?n(G(this.arrival?.route_type),{size:16,label:this._t("vehicleHere")}):A?n(m.myStop,{size:16}):a}
              </div>
            </div>
            <div>
              <div class="stop-title">${e.name}</div>
              <div class="stop-sub">
                ${A?o`<span class="mine-label">${this._t("myStop")}</span> · `:a}${[e.city,e.code].filter(Boolean).join(" \xB7 ")}
              </div>
            </div>
            ${e.arrival_time?o`<div class="time ltr">${Q(e.arrival_time,this.hass)}</div>`:o`<div class="time">${this._relative(e.offset_seconds)}</div>`}
          </button>
        </li>`})}
    </ol>`}};l(A1,"properties",{...P.properties,arrival:{attribute:!1},showMap:{attribute:!1},stopCode:{attribute:!1},clockOffset:{attribute:!1},_route:{state:!0},_now:{state:!0}});var R5=300,F5=M=>Object.fromEntries(Object.entries(M).filter(([C,H])=>H!=null&&H!==""&&!(Array.isArray(H)&&H.length===0)&&b[C]!==H)),X=class extends Z{constructor(){super(),this._results=[],this._routes=[],this._searching=!1,this._searched=!1,this._picking=!1}connectedCallback(){super.connectedCallback(),this._config?.stop_code&&!this._stop&&this._loadStop()}disconnectedCallback(){super.disconnectedCallback(),clearTimeout(this._searchTimer)}updated(C){C.has("hass")&&!C.get("hass")&&!this._stop&&this._loadStop()}setConfig(C){this._config={...C},C.stop_code&&Number(this._stop?.code)!==Number(C.stop_code)&&this._loadStop()}_t(C){return S(this.hass,C)}async _loadStop(){if(!this.hass||!this._config?.stop_code)return;let C=Number(this._config.stop_code);try{let[H,V]=await Promise.all([this.hass.callWS({type:`${c}/stop`,stop_code:C}),this.hass.callWS({type:`${c}/stop_routes`,stop_code:C})]);if(C!==Number(this._config?.stop_code))return;this._stop=H.stop,this._routes=V}catch{if(C!==Number(this._config?.stop_code))return;this._stop={code:C,name:""},this._routes=[]}}_onSearchInput(C){if(this._query=C.target.value??"",clearTimeout(this._searchTimer),this._query.trim().length<2){this._results=[],this._searched=!1;return}let H=this._query.trim();this._searchTimer=setTimeout(()=>this._search(H),R5)}async _search(C){if(!this.hass)return;let H=this._searchSeq=(this._searchSeq||0)+1;this._searching=!0;let V=[];try{V=await this.hass.callWS({type:`${c}/search_stops`,query:C,limit:30})}catch{V=[]}H===this._searchSeq&&(this._results=V,this._searching=!1,this._searched=!0)}_pick(C){this._stop=C,this._close(),this._emit({...this._config,stop_code:C.code,lines:[]}),this._loadRoutes(C.code)}_close(){this._results=[],this._searched=!1,this._picking=!1,this._query=""}async _loadRoutes(C){try{this._routes=await this.hass.callWS({type:`${c}/stop_routes`,stop_code:Number(C)})}catch{this._routes=[]}}get _routesByLine(){let C=new Map;for(let H of this._routes){let V=String(H.line_name);C.has(V)||C.set(V,H)}return C}get _lines(){return(this._config?.lines||[]).map(String)}_setLines(C){this._emit({...this._config,lines:C})}_move(C,H){let V=[...this._lines],L=C+H;L<0||L>=V.length||([V[C],V[L]]=[V[L],V[C]],this._emit({...this._config,lines:V,order:"lines"}))}_removeLine(C){this._setLines(this._lines.filter((H,V)=>V!==C))}_addLine(C){this._setLines([...this._lines,C])}_emit(C){this._config=F5(C),U2(this,"config-changed",{config:this._config})}_set(C,H){this._emit({...this._config,[C]:H})}_setNumber(C,H,V,L){let r=Number.parseInt(H,10);this._set(C,Number.isNaN(r)?b[C]:Math.min(L,Math.max(V,r)))}get _value(){return{...b,...this._config}}_renderText(C,H,V){let L=`it-${C}`;return o`<div class="field">
      <label for=${L}>${H}</label>
      <input
        id=${L}
        type="text"
        .value=${this._config[C]??""}
        @change=${r=>this._set(C,r.target.value.trim())}
      />
      ${V?o`<span class="hint">${V}</span>`:a}
    </div>`}_renderNumber(C,H,V,L,r){let e=`it-${C}`;return o`<div class="field">
      <label for=${e}>${H}</label>
      <input
        id=${e}
        type="number"
        inputmode="numeric"
        min=${V}
        max=${L}
        step="1"
        .value=${String(this._value[C])}
        @change=${t=>this._setNumber(C,t.target.value,V,L)}
      />
      ${r?o`<span class="hint">${r}</span>`:a}
    </div>`}_renderSwitch(C,H,V){let L=`it-${C}`;return o`<label class="switch-row" for=${L}>
      <span class="switch-text">
        <span>${H}</span>
        ${V?o`<span class="hint">${V}</span>`:a}
      </span>
      <input
        id=${L}
        class="switch"
        type="checkbox"
        role="switch"
        .checked=${!!this._value[C]}
        @change=${r=>this._set(C,r.target.checked)}
      />
    </label>`}_renderOptions(){let C=this._routes.some(V=>String(V.route_type)==="2"),H=[["show_header","editorShowHeader"],["show_city","editorShowCity"],["show_stop_code","editorShowStopCode"],["show_destination","editorShowDestination"],["show_operator","editorShowOperator"],["show_mode_icon","editorShowModeIcon"],["show_realtime_tag","editorShowRealtimeTag"],["show_platform","editorShowPlatform"],["show_delay","editorShowDelay"],["show_clock","editorShowClock"]];return o`
      ${this._renderText("title",this._t("editorTitle"))}
      <div class="grid">
        ${this._renderNumber("max_arrivals",this._t("editorMaxArrivals"),1,20)}
        ${this._renderNumber("max_lines",this._t("editorMaxLines"),0,20,this._t("editorMaxLinesHelp"))}
      </div>
      ${this._lines.length?o`<div class="field">
            <label for="it-order">${this._t("editorOrder")}</label>
            <select id="it-order" @change=${V=>this._set("order",V.target.value)}>
              <option value="time" ?selected=${this._value.order!=="lines"}>
                ${this._t("editorOrderTime")}
              </option>
              <option value="lines" ?selected=${this._value.order==="lines"}>
                ${this._t("editorOrderLines")}
              </option>
            </select>
          </div>`:a}
      ${this._renderSwitch("show_map",this._t("editorShowMap"),this._t("editorShowMapHelp"))}
      <details class="expandable">
        <summary>
          ${n(m.chevron,{size:20,cls:"icon summary-chevron"})}
          <span>${this._t("editorDisplay")}</span>
        </summary>
        <div class="switches">
          ${H.map(([V,L])=>this._renderSwitch(V,this._t(L)))}
        </div>
      </details>
      ${C?this._renderText("rail_destination",this._t("mode_2")):a}
    `}render(){if(!this._config||!this.hass)return a;let C=!this._config.stop_code||this._picking;return o`
      <div class="box">
        <div class="brand">
          <img src=${W2} alt="" aria-hidden="true" />
          <span class="brand-name">${this._t("name")}</span>
        </div>
        ${C?this._renderSearch():this._renderSelected()}
        ${this._config.stop_code?o`
              ${this._renderLines()} ${this._renderOptions()}
            `:a}
      </div>
    `}_renderSelected(){let C=this._stop||{code:this._config.stop_code};return o`
      <div class="selected">
        ${n(m.busStop,{size:24})}
        <div class="selected-body">
          <div class="selected-name">${C.name||this._t("stop")}</div>
          <div class="selected-sub">
            ${[C.street,C.city,C.code].filter(Boolean).join(" \xB7 ")}
          </div>
        </div>
        <button class="chip" @click=${()=>this._picking=!0}>
          ${this._t("editorChange")}
        </button>
      </div>
    `}_renderSearch(){return o`
      <div class="field">
        <div class="row">
          <label for="it-search">${this._t("editorSearch")}</label>
          ${this._config.stop_code?o`<button
                class="tool"
                title=${this._t("editorCancel")}
                aria-label=${this._t("editorCancel")}
                @click=${this._close}
              >
                ${n(m.close)}
              </button>`:a}
        </div>
        <input
          id="it-search"
          type="search"
          autocomplete="off"
          .value=${this._query??""}
          @input=${this._onSearchInput}
        />
        <span class="hint">${this._t("editorSearchHelp")}</span>
      </div>
      ${this._searching?o`<div class="hint">${this._t("editorSearching")}</div>`:this._results.length?o`<div class="results">
              ${this._results.map(C=>o`
                  <button class="result" @click=${()=>this._pick(C)}>
                    <div class="result-name">${C.name}</div>
                    <div class="result-sub">
                      ${[C.street,C.city,C.code].filter(Boolean).join(" \xB7 ")}
                    </div>
                  </button>
                `)}
            </div>`:this._searched?o`<div class="hint">${this._t("editorNoResults")}</div>`:a}
    `}_renderLines(){let C=this._routesByLine,H=this._lines,V=[...C.keys()].filter(L=>!H.includes(L));return o`
      <div class="section">
        <div class="section-title">${this._t("editorLines")}</div>
        ${H.length?H.map((L,r)=>this._renderChosenLine(L,r,H.length,C.get(L))):o`<div class="hint">${this._t("editorLinesHelp")}</div>`}
        ${V.length?o`<div class="chips">
              ${V.map(L=>this._renderAddChip(L,C.get(L)))}
            </div>`:C.size?o`<div class="hint">${this._t("editorAllShown")}</div>`:a}
      </div>
    `}_renderChosenLine(C,H,V,L){return o`
      <div class="line">
        <div
          class="badge"
          style=${`--it-badge-color:${y(L?.route_type)}`}
        >
          ${C}
        </div>
        <div class="line-body">
          <div class="line-sub">
            ${[L?.destination,L?.operator].filter(Boolean).join(" \xB7 ")}
          </div>
        </div>
        <div class="tools">
          <button
            class="tool"
            ?disabled=${H===0}
            title=${this._t("editorMoveUp")}
            aria-label=${this._t("editorMoveUp")}
            @click=${()=>this._move(H,-1)}
          >
            ${n(m.arrowUp)}
          </button>
          <button
            class="tool"
            ?disabled=${H===V-1}
            title=${this._t("editorMoveDown")}
            aria-label=${this._t("editorMoveDown")}
            @click=${()=>this._move(H,1)}
          >
            ${n(m.arrowDown)}
          </button>
          <button
            class="tool"
            title=${this._t("editorRemove")}
            aria-label=${this._t("editorRemove")}
            @click=${()=>this._removeLine(H)}
          >
            ${n(m.close)}
          </button>
        </div>
      </div>
    `}_renderAddChip(C,H){return o`
      <button
        class="chip"
        style=${`--it-badge-color:${y(H?.route_type)}`}
        title=${`${this._t("editorAddLine")}: ${C}`}
        @click=${()=>this._addLine(C)}
      >
        <span class="swatch"></span>
        <span class="line-name">${C}</span>
      </button>
    `}};l(X,"properties",{hass:{attribute:!1},_config:{state:!0},_stop:{state:!0},_routes:{state:!0},_results:{state:!0},_searching:{state:!0},_searched:{state:!0},_picking:{state:!0}}),l(X,"styles",[K,O`
      .box {
        display: flex;
        flex-direction: column;
        gap: var(--ha-space-4, 16px);
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: var(--ha-space-4, 16px);
      }

      .field select,
      .field input[type="text"],
      .field input[type="number"] {
        width: 100%;
        box-sizing: border-box;
        min-height: 48px;
        padding: var(--ha-space-3, 12px) var(--ha-space-4, 16px);
        border: var(--ha-border-width-sm, 1px) solid var(--ha-color-border-neutral-normal, rgba(127, 127, 127, 0.4));
        border-radius: var(--ha-border-radius-md, 8px);
        background: var(--ha-color-surface-default, var(--card-background-color));
        color: var(--primary-text-color);
        font: inherit;
        font-size: var(--ha-font-size-l, 16px);
      }

      .field select:focus-visible,
      .field input:focus-visible {
        outline: 2px solid var(--ha-color-focus, var(--primary-color));
        outline-offset: 2px;
      }

      .switch-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--ha-space-4, 16px);
        min-height: 48px;
        cursor: pointer;
      }

      .switch-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
        font-size: var(--ha-font-size-m, 14px);
        color: var(--primary-text-color);
      }

      /* A switch built on a checkbox, in Home Assistant's proportions. */
      .switch {
        appearance: none;
        flex: 0 0 auto;
        position: relative;
        width: 36px;
        height: 20px;
        margin: 0;
        border-radius: var(--ha-border-radius-pill, 9999px);
        background: var(--ha-color-fill-neutral-loud-resting, rgba(127, 127, 127, 0.55));
        cursor: pointer;
        transition: background-color var(--ha-animation-duration-fast, 150ms);
      }

      .switch::after {
        content: "";
        position: absolute;
        inset-block-start: 2px;
        inset-inline-start: 2px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #fff;
        transition: inset-inline-start var(--ha-animation-duration-fast, 150ms);
      }

      .switch:checked {
        background: var(--primary-color);
      }

      .switch:checked::after {
        inset-inline-start: 18px;
      }

      .switch:focus-visible {
        outline: 2px solid var(--ha-color-focus, var(--primary-color));
        outline-offset: 2px;
      }

      @media (prefers-reduced-motion: reduce) {
        .switch,
        .switch::after {
          transition: none;
        }
      }

      .expandable {
        border: var(--ha-border-width-sm, 1px) solid var(--divider-color, rgba(127, 127, 127, 0.3));
        border-radius: var(--ha-border-radius-lg, 12px);
      }

      .expandable summary {
        display: flex;
        align-items: center;
        gap: var(--ha-space-2, 8px);
        min-height: 48px;
        padding-inline: var(--ha-space-3, 12px);
        list-style: none;
        cursor: pointer;
        font-size: var(--ha-font-size-m, 14px);
        font-weight: var(--ha-font-weight-medium, 500);
        color: var(--primary-text-color);
      }

      .expandable summary::-webkit-details-marker {
        display: none;
      }

      .expandable summary:focus-visible {
        outline: 2px solid var(--ha-color-focus, var(--primary-color));
        outline-offset: -2px;
        border-radius: var(--ha-border-radius-lg, 12px);
      }

      .summary-chevron {
        color: var(--secondary-text-color);
        transition: transform var(--ha-animation-duration-fast, 150ms);
      }

      :host(:dir(rtl)) .summary-chevron {
        transform: scaleX(-1);
      }

      .expandable[open] .summary-chevron {
        transform: rotate(90deg);
      }

      .switches {
        display: flex;
        flex-direction: column;
        padding: 0 var(--ha-space-4, 16px) var(--ha-space-2, 8px);
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-block-end: -4px;
      }

      .brand img {
        width: 28px;
        height: 28px;
        flex: 0 0 auto;
      }

      .brand-name {
        font-size: 0.9375rem;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      .selected {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 12px;
        border-radius: 10px;
        background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.12));
      }

      .selected-body {
        flex: 1 1 auto;
        min-width: 0;
      }

      .selected-name {
        color: var(--primary-text-color);
        overflow-wrap: anywhere;
      }

      .selected-sub {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }

      /* The stop search; see the note above this stylesheet. */
      .field {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .field label {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }

      .field input {
        width: 100%;
        box-sizing: border-box;
        padding: 12px 14px;
        border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.4));
        border-radius: 10px;
        background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.1));
        color: var(--primary-text-color);
        font: inherit;
        font-size: 1rem;
      }

      .field input:focus {
        outline: none;
        border-color: var(--primary-color);
      }

      .row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .results {
        display: flex;
        flex-direction: column;
        max-height: 260px;
        overflow-y: auto;
        border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.3));
        border-radius: 10px;
      }

      .result {
        display: block;
        width: 100%;
        padding: 10px 12px;
        border: none;
        border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
        background: none;
        color: inherit;
        font: inherit;
        text-align: start;
        cursor: pointer;
      }

      .result:first-child {
        border-top: none;
      }

      .result:hover,
      .result:focus-visible {
        background: var(--ha-color-surface-lower, rgba(127, 127, 127, 0.1));
      }

      .result-name {
        color: var(--primary-text-color);
      }

      .result-sub {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }

      .hint {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
      }

      /* -- the ordered line list -- */

      .section {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }

      .section-title {
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--primary-text-color);
      }

      .line {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 6px 8px;
        border-radius: 10px;
        background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.12));
      }

      .line .badge {
        min-width: 38px;
        font-size: 0.875rem;
      }

      .line-body {
        flex: 1 1 auto;
        min-width: 0;
      }

      .line-sub {
        font-size: 0.75rem;
        color: var(--secondary-text-color);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .tools {
        display: flex;
        flex: 0 0 auto;
        gap: 2px;
      }

      .tool {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 40px;
        height: 40px;
        padding: 0;
        border: none;
        border-radius: 50%;
        background: none;
        color: var(--secondary-text-color);
        cursor: pointer;
      }

      .tool:hover:not(:disabled) {
        background: var(--ha-color-surface-lower, rgba(127, 127, 127, 0.14));
        color: var(--primary-text-color);
      }

      .tool:disabled {
        opacity: 0.35;
        cursor: default;
      }

      .chips {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 5px 10px;
        border: 1px solid var(--divider-color, rgba(127, 127, 127, 0.35));
        border-radius: 16px;
        background: none;
        color: var(--primary-text-color);
        font: inherit;
        font-size: 0.8125rem;
        cursor: pointer;
      }

      .chip:hover,
      .chip:focus-visible {
        background: var(--ha-color-surface-lower, rgba(127, 127, 127, 0.12));
      }

      .chip .swatch {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--it-badge-color, var(--it-mode-unknown));
      }

      .line-name {
        font-variant-numeric: tabular-nums;
        direction: ltr;
        unicode-bidi: isolate;
      }
    `]);var K2=new URL("./vendor/maplibre-6.19.0/",import.meta.url),q2={light:"https://tiles.versatiles.org/assets/styles/gray/style.json",dark:"https://tiles.versatiles.org/assets/styles/gray-dark/style.json"},D5=["noto_sans_regular"],E5=["noto_sans_bold"],j2=16,s1="it-arrow",$5=2e3,N5=250,W5=500,u1=null,I5=()=>(u1??=Promise.all([import(new URL("maplibre-gl.mjs",K2).href),fetch(new URL("maplibre-gl.css",K2)).then(M=>{if(!M.ok)throw new Error(`maplibre-gl.css: HTTP ${M.status}`);return M.text()})]).then(([M,C])=>{let H=new CSSStyleSheet;return H.replaceSync(C),{maplibre:M,sheet:H}}),u1.catch(()=>{u1=null}),u1),S1=null,z5=()=>{if(S1===null)try{S1=!!document.createElement("canvas").getContext("webgl2")}catch{S1=!1}return S1},$=null,X2=$2(M=>{if($??=document.createElement("canvas").getContext("2d",{willReadFrequently:!0}),!$||!CSS.supports("color",M))return null;$.clearRect(0,0,1,1),$.fillStyle="#000",$.fillStyle=M,$.fillRect(0,0,1,1);let[C,H,V,L]=$.getImageData(0,0,1,1).data;return L===255?`rgb(${C}, ${H}, ${V})`:`rgba(${C}, ${H}, ${V}, ${(L/255).toFixed(3)})`}),U5=()=>{let C=document.createElement("canvas");C.width=C.height=32;let H=C.getContext("2d");return H.strokeStyle="#fff",H.lineWidth=5,H.lineCap="round",H.lineJoin="round",H.beginPath(),H.moveTo(11,8),H.lineTo(21,16),H.lineTo(11,24),H.stroke(),H.getImageData(0,0,32,32)},z1=M=>({type:"Feature",properties:{},geometry:{type:"LineString",coordinates:(M||[]).map(k)}}),Y2=M=>({type:"FeatureCollection",features:M}),Y=class extends Z{constructor(){super(),this.view=null,this.strings={},this._status="loading",this._moved=!1}connectedCallback(){super.connectedCallback(),this.hasUpdated&&this._start()}disconnectedCallback(){super.disconnectedCallback(),this._stop()}firstUpdated(){this._start()}updated(C){C.has("view")&&(this.toggleAttribute("dark",!!this.view?.dark),this._apply(C.get("view")))}focusOn(C){!this._map||!C||(this._moved=!0,this._map.easeTo({center:k(C),zoom:Math.max(this._map.getZoom(),15),duration:E()?0:350}))}async _start(){if(this._map||this._starting)return;if(!z5()){this._status="unsupported";return}this._status="loading";let C=this._generation=(this._generation??0)+1;this._starting=!0;let H;try{H=await I5()}catch{this._starting=!1,C===this._generation&&(this._status="vendor");return}if(this._starting=!1,C!==this._generation||!this.isConnected)return;let{maplibre:V,sheet:L}=H;this._maplibre=V,this.shadowRoot.adoptedStyleSheets.includes(L)||(this.shadowRoot.adoptedStyleSheets=[...this.shadowRoot.adoptedStyleSheets,L]);let r=this.renderRoot.querySelector("#map"),e=getComputedStyle(this).direction==="rtl";this._dark=!!this.view?.dark,this._styleLoaded=!1;let t;try{t=new V.Map({container:r,style:q2[this._dark?"dark":"light"],transformStyle:(A,d)=>this._withRoute(d),bounds:this.view?.bounds??void 0,fitBoundsOptions:this._fitOptions(),maxZoom:19,attributionControl:{compact:!0},dragRotate:!1,pitchWithRotate:!1,touchPitch:!1,renderWorldCopies:!1,locale:this.strings.maplibre,fadeDuration:E()?0:300})}catch{this._status="failed";return}this._map=t,t.touchZoomRotate.disableRotation(),t.keyboard.disableRotation(),t.addControl(new V.NavigationControl({showCompass:!1}),e?"top-left":"top-right"),t.once("idle",()=>{r.querySelector(".maplibregl-ctrl-attrib.maplibregl-compact-show")?.classList.remove("maplibregl-compact-show")}),t.on("styleimagemissing",A=>{A.id===s1&&!t.hasImage(s1)&&t.addImage(s1,U5(),{sdf:!0,pixelRatio:2})}),t.on("style.load",()=>{this._styleLoaded=!0,this._status="ready",this._syncSources()}),t.on("error",A=>{A.tile||A.sourceId||this._styleLoaded||(this._status="unavailable")});let i=A=>{A.originalEvent&&(this._moved=!0)};t.on("dragstart",i),t.on("zoomstart",i),t.on("webglcontextlost",()=>{clearTimeout(this._contextTimer),this._contextTimer=setTimeout(()=>this._status="failed",$5)}),t.on("webglcontextrestored",()=>{clearTimeout(this._contextTimer),this._status==="failed"&&(this._status="ready")}),this._resize=new ResizeObserver(()=>{t.resize(),!this._fitted&&r.clientWidth&&r.clientHeight&&this._fit(!1)}),this._resize.observe(r),this._updateMarkers()}_stop(){this._generation=(this._generation??0)+1,this._starting=!1,cancelAnimationFrame(this._glide),clearTimeout(this._contextTimer),this._resize?.disconnect(),this._resize=void 0,this._vehicleMarker=void 0,this._mineMarker=void 0;try{this._map?.remove()}catch{}this._map=void 0,this._fitted=!1}_retry(){this._stop(),this._start()}get _colors(){let C=this.view||{},H=!!C.dark;return{route:X2(C.color,H?"#66bb6a":"#2f7d4f"),casing:H?"#1c1c1c":"#ffffff",halo:H?"rgba(28, 28, 28, 0.9)":"rgba(255, 255, 255, 0.92)",text:H?"#e1e1e1":"#212121",stopFill:H?"#2a2a2a":"#ffffff",mine:X2(C.mineColor,H?"#ffb300":"#9c6200")}}_sources(){let C=this.view||{},H=(C.stops||[]).map(L=>({type:"Feature",properties:{name:L.name??"",done:!!L.done},geometry:{type:"Point",coordinates:k(L.point)}})),V=C.mine?[{type:"Feature",properties:{name:C.mine.name??""},geometry:{type:"Point",coordinates:k(C.mine.point)}}]:[];return{"it-line":z1(C.line),"it-done":z1(C.done),"it-ahead":z1(C.ahead??C.line),"it-stops":Y2(H),"it-mine":Y2(V)}}_layers(){let C=this._colors,H=!!this.view?.dashed,V=(e,t)=>["interpolate",["linear"],["zoom"],10,e,16,t],L=[{id:"it-casing",type:"line",source:"it-line",layout:{"line-cap":"round","line-join":"round"},paint:{"line-color":C.casing,"line-width":V(6,11)}},{id:"it-done",type:"line",source:"it-done",layout:{"line-cap":"round","line-join":"round"},paint:{"line-color":C.route,"line-width":V(3,6),"line-opacity":.35}},{id:"it-ahead",type:"line",source:"it-ahead",layout:{"line-cap":H?"butt":"round","line-join":"round"},paint:{"line-color":C.route,"line-width":V(3,6),...H?{"line-dasharray":[2,1.5]}:{}}},{id:"it-arrows",type:"symbol",source:"it-ahead",minzoom:13,layout:{"symbol-placement":"line","symbol-spacing":90,"icon-image":s1,"icon-size":["interpolate",["linear"],["zoom"],13,.45,17,.7],"icon-allow-overlap":!0,"icon-ignore-placement":!0,"icon-rotation-alignment":"map"},paint:{"icon-color":C.casing,"icon-opacity":.95}}],r=[{id:"it-stops",type:"circle",source:"it-stops",paint:{"circle-radius":["interpolate",["linear"],["zoom"],10,2.5,16,5.5],"circle-color":C.stopFill,"circle-stroke-color":C.route,"circle-stroke-width":["interpolate",["linear"],["zoom"],10,1.5,16,2.5],"circle-opacity":["case",["get","done"],.55,1],"circle-stroke-opacity":["case",["get","done"],.45,1]}},{id:"it-stop-labels",type:"symbol",source:"it-stops",minzoom:15,layout:{"text-field":["get","name"],"text-font":D5,"text-size":12,"text-offset":[0,1],"text-anchor":"top","text-max-width":9,"symbol-sort-key":2},paint:{"text-color":C.text,"text-halo-color":C.halo,"text-halo-width":1.6,"text-opacity":["case",["get","done"],.6,1]}},{id:"it-mine-label",type:"symbol",source:"it-mine",layout:{"text-field":["get","name"],"text-font":E5,"text-size":13,"text-offset":[0,.9],"text-anchor":"top","text-max-width":9,"text-allow-overlap":!0,"text-ignore-placement":!0,"symbol-sort-key":0},paint:{"text-color":C.text,"text-halo-color":C.halo,"text-halo-width":2}}];return{under:L,over:r}}_withRoute(C){let H=Object.fromEntries(Object.entries(this._sources()).map(([i,A])=>[i,{type:"geojson",data:A}])),{under:V,over:L}=this._layers(),r=[...C.layers||[]],e=r.findIndex(i=>i.type==="symbol"),t=e<0?r.length:e;return r.splice(t,0,...V),r.push(...L),{...C,sources:{...C.sources,...H},layers:r}}_apply(C){let H=this._map;if(!H)return;let V=this.view||{},L=!!V.dark;L!==this._dark?(this._dark=L,this._styleLoaded=!1,H.setStyle(q2[L?"dark":"light"])):this._styleLoaded&&(this._syncSources(),(C?.color!==V.color||C?.dashed!==V.dashed)&&this._repaint()),this._updateMarkers(),V.fitKey!==C?.fitKey&&(V.subject!==C?.subject&&(this._moved=!1),this._moved||this._fit(!!this._fitted))}_syncSources(){let C=this._map;if(C)for(let[H,V]of Object.entries(this._sources()))C.getSource(H)?.setData(V)}_repaint(){let C=this._map,{under:H,over:V}=this._layers();for(let L of[...H,...V])if(C.getLayer(L.id))for(let[r,e]of Object.entries(L.paint||{}))C.setPaintProperty(L.id,r,e);if(C.getLayer("it-ahead")){let L=!!this.view?.dashed;C.setPaintProperty("it-ahead","line-dasharray",L?[2,1.5]:void 0),C.setLayoutProperty("it-ahead","line-cap",L?"butt":"round")}}_fitOptions(){return{padding:48,maxZoom:j2}}_fit(C){let H=this._map,V=this.view?.bounds;if(!H||!V)return;let L=H.getContainer();if(!L.clientWidth||!L.clientHeight)return;let r=V[0][0]===V[1][0]&&V[0][1]===V[1][1],e={...this._fitOptions(),duration:C&&!E()?350:0};if(r)H.jumpTo({center:V[0],zoom:j2-1});else{let t=L.clientWidth>120&&L.clientHeight>120;H.fitBounds(V,t?e:{...e,padding:8})}this._fitted=!0}recenter(){this._moved=!1,this._fit(!0)}_updateMarkers(){let C=this._map,H=this._maplibre;if(!C||!H)return;let V=this.view||{},L=this._colors,r={"--it-color":L.route,"--it-casing":L.casing,"--it-text":L.text,"--it-mine":L.mine,"--it-stale":V.dark?"#757575":"#9e9e9e"};if(V.mine){if(!this._mineMarker){let A=document.createElement("div");A.className="mine",A.innerHTML=E1(m.myStop,30),this._mineMarker=new H.Marker({element:A,anchor:"bottom"}).setLngLat(k(V.mine.point)).addTo(C)}let i=this._mineMarker.getElement();Object.entries(r).forEach(([A,d])=>i.style.setProperty(A,d)),i.setAttribute("role","img"),i.setAttribute("aria-label",V.mine.label??V.mine.name??""),this._mineMarker.setLngLat(k(V.mine.point))}else this._mineMarker?.remove(),this._mineMarker=void 0;let e=V.vehicle;if(!e){cancelAnimationFrame(this._glide),this._vehicleMarker?.remove(),this._vehicleMarker=void 0;return}if(!this._vehicleMarker){let i=document.createElement("div");i.className="vehicle",i.innerHTML='<span class="pulse"></span><span class="dot"></span><span class="line"></span>',this._vehicleMarker=new H.Marker({element:i}).setLngLat(k(e.point)).addTo(C)}let t=this._vehicleMarker.getElement();Object.entries(r).forEach(([i,A])=>t.style.setProperty(i,A)),t.classList.toggle("stale",!!e.stale),t.querySelector(".dot").innerHTML=E1(e.icon,16),t.querySelector(".line").textContent=e.lineName??"",t.setAttribute("role","img"),t.setAttribute("aria-label",e.label??""),this._glideTo(e.point)}_glideTo(C){let H=this._vehicleMarker;cancelAnimationFrame(this._glide);let{lng:V,lat:L}=H.getLngLat(),r=[L,V];if(r[0]===C[0]&&r[1]===C[1])return;if(E()||x1(r,C)>W5){H.setLngLat(k(C));return}let e=performance.now(),t=i=>{let A=Math.min(1,(i-e)/N5),d=1-(1-A)**3;H.setLngLat([r[1]+(C[1]-r[1])*d,r[0]+(C[0]-r[0])*d]),A<1&&(this._glide=requestAnimationFrame(t))};this._glide=requestAnimationFrame(t)}render(){let C=this.strings,H={unsupported:C.unsupported,unavailable:C.unavailable,failed:C.failed,vendor:C.vendor}[this._status];return o`
      <div id="map" ?hidden=${!!H}></div>
      ${H?o`<div class="status" role="status">
            ${n(m.noPosition,{size:28})}
            <span>${H}</span>
            ${this._status==="unsupported"?a:o`<button @click=${this._status==="vendor"?()=>location.reload():this._retry}>
                  ${this._status==="vendor"?C.reload:C.retry}
                </button>`}
          </div>`:a}
      ${this._moved&&!H&&this.view?.bounds?o`<button class="recenter" @click=${this.recenter}>
            ${n(m.recenter,{size:18})}<span>${C.recenter}</span>
          </button>`:a}
    `}};l(Y,"properties",{view:{attribute:!1},strings:{attribute:!1},_status:{state:!0},_moved:{state:!0}}),l(Y,"styles",O`
    :host {
      position: relative;
      display: block;
      overflow: hidden;
      border-radius: var(--ha-border-radius-lg, 12px);
      background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.12));
      /* A drag on the map moves the map, never the sheet around it. */
      touch-action: none;
    }

    #map {
      position: absolute;
      inset: 0;
    }

    .status {
      position: absolute;
      inset: 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: var(--ha-space-2, 8px);
      padding: var(--ha-space-4, 16px);
      text-align: center;
      font-size: var(--ha-font-size-m, 14px);
      color: var(--secondary-text-color);
    }

    .status button {
      min-height: 36px;
      padding-inline: var(--ha-space-4, 16px);
      border: var(--ha-border-width-sm, 1px) solid var(--divider-color);
      border-radius: var(--ha-border-radius-pill, 9999px);
      background: var(--card-background-color);
      color: var(--primary-text-color);
      font: inherit;
      cursor: pointer;
    }

    .recenter {
      position: absolute;
      inset-block-end: var(--ha-space-3, 12px);
      inset-inline-end: var(--ha-space-3, 12px);
      display: inline-flex;
      align-items: center;
      gap: var(--ha-space-2, 8px);
      min-height: 40px;
      padding-inline: var(--ha-space-3, 12px) var(--ha-space-4, 16px);
      border: none;
      border-radius: var(--ha-border-radius-pill, 9999px);
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color);
      box-shadow: var(--ha-box-shadow-m, 0 3px 6px -1px rgba(0, 0, 0, 0.1), 0 8px 16px -2px rgba(0, 0, 0, 0.15));
      font: inherit;
      font-size: var(--ha-font-size-s, 12px);
      font-weight: var(--ha-font-weight-medium, 500);
      cursor: pointer;
    }

    button:focus-visible {
      outline: 2px solid var(--ha-color-focus, var(--primary-color));
      outline-offset: 2px;
    }

    /* -- markers: MapLibre moves these with transform, so nothing on the
       marker element itself may transition, only what is inside it. -- */

    .vehicle {
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 34px;
      height: 34px;
    }

    .vehicle .dot {
      position: relative;
      z-index: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 30px;
      height: 30px;
      border: 3px solid var(--it-casing);
      border-radius: 50%;
      box-sizing: border-box;
      background: var(--it-color);
      color: #fff;
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
    }

    .vehicle .line {
      position: absolute;
      z-index: 2;
      inset-block-start: -10px;
      inset-inline-start: 22px;
      padding: 1px 6px;
      border-radius: var(--ha-border-radius-pill, 9999px);
      background: var(--it-casing);
      color: var(--it-text);
      font-size: 11px;
      font-weight: 700;
      line-height: 16px;
      white-space: nowrap;
      direction: ltr;
      unicode-bidi: isolate;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
    }

    .vehicle .pulse {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background: var(--it-color);
      opacity: 0.35;
      animation: pulse 2s ease-out infinite;
    }

    .vehicle.stale .dot {
      background: var(--it-stale);
      border-style: dashed;
    }

    .vehicle.stale .pulse {
      display: none;
    }

    @keyframes pulse {
      from {
        transform: scale(1);
        opacity: 0.4;
      }
      to {
        transform: scale(2.2);
        opacity: 0;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .vehicle .pulse {
        animation: none;
        display: none;
      }
    }

    /* MapLibre's own controls, in the card's colours rather than its white. */
    .maplibregl-ctrl-group,
    .maplibregl-ctrl-attrib {
      background: var(--card-background-color, #fff) !important;
      color: var(--primary-text-color);
    }

    .maplibregl-ctrl-group {
      border-radius: var(--ha-border-radius-md, 8px) !important;
      box-shadow: var(--ha-box-shadow-s, 0 1px 2px 0 rgba(0, 0, 0, 0.08), 0 1px 3px 0 rgba(0, 0, 0, 0.12)) !important;
    }

    .maplibregl-ctrl-group button + button {
      border-top-color: var(--divider-color, rgba(127, 127, 127, 0.2)) !important;
    }

    .maplibregl-ctrl-attrib a {
      color: var(--secondary-text-color);
    }

    :host([dark]) .maplibregl-ctrl-icon,
    :host([dark]) .maplibregl-ctrl-attrib-button {
      filter: invert(1);
    }

    .mine {
      display: flex;
      color: var(--it-mine);
      filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.45));
    }
  `);var J=(M,C)=>{customElements.get(M)||customElements.define(M,C)};J("israel-transit-card",q);J("israel-transit-card-editor",X);J("israel-transit-stop-dialog",a1);J("israel-transit-route-dialog",A1);J("israel-transit-dialog",j);J("israel-transit-map",Y);var J2={locale:{language:navigator.language||"he"}};window.customCards=window.customCards||[];window.customCards.some(M=>M.type==="israel-transit-card")||window.customCards.push({type:"israel-transit-card",name:S(J2,"name"),description:S(J2,"description"),preview:!0,documentationURL:"https://github.com/yosef-chai/israel-transit",getEntitySuggestion:(M,C)=>{if(M?.entities?.[C]?.platform!==c)return null;let H=M.states?.[C]?.attributes?.stop_code;return H?{config:{type:"custom:israel-transit-card",stop_code:Number(H)}}:null}});console.info("%c ISRAEL-TRANSIT-CARD %c v1.5.0 ","background:#2f7d4f;color:#fff;border-radius:3px 0 0 3px;padding:2px 4px","background:#1e6fbf;color:#fff;border-radius:0 3px 3px 0;padding:2px 4px");
