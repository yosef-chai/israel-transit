/* Israel Transit card - https://github.com/yosef-chai/israel-transit */
var re=Object.defineProperty;var ne=(o,t,e)=>t in o?re(o,t,{enumerable:!0,configurable:!0,writable:!0,value:e}):o[t]=e;var m=(o,t,e)=>ne(o,typeof t!="symbol"?t+"":t,e);var X=globalThis,Y=X.ShadowRoot&&(X.ShadyCSS===void 0||X.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,ot=Symbol(),wt=new WeakMap,H=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==ot)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o,e=this.t;if(Y&&t===void 0){let i=e!==void 0&&e.length===1;i&&(t=wt.get(e)),t===void 0&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),i&&wt.set(e,t))}return t}toString(){return this.cssText}},x=o=>new H(typeof o=="string"?o:o+"",void 0,ot),w=(o,...t)=>{let e=o.length===1?o[0]:t.reduce((i,s,r)=>i+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+o[r+1],o[0]);return new H(e,o,ot)},St=(o,t)=>{if(Y)o.adoptedStyleSheets=t.map(e=>e instanceof CSSStyleSheet?e:e.styleSheet);else for(let e of t){let i=document.createElement("style"),s=X.litNonce;s!==void 0&&i.setAttribute("nonce",s),i.textContent=e.cssText,o.appendChild(i)}},rt=Y?o=>o:o=>o instanceof CSSStyleSheet?(t=>{let e="";for(let i of t.cssRules)e+=i.cssText;return x(e)})(o):o;var{is:ae,defineProperty:le,getOwnPropertyDescriptor:ce,getOwnPropertyNames:he,getOwnPropertySymbols:de,getPrototypeOf:pe}=Object,J=globalThis,At=J.trustedTypes,ue=At?At.emptyScript:"",_e=J.reactiveElementPolyfillSupport,I=(o,t)=>o,nt={toAttribute(o,t){switch(t){case Boolean:o=o?ue:null;break;case Object:case Array:o=o==null?o:JSON.stringify(o)}return o},fromAttribute(o,t){let e=o;switch(t){case Boolean:e=o!==null;break;case Number:e=o===null?null:Number(o);break;case Object:case Array:try{e=JSON.parse(o)}catch{e=null}}return e}},Ct=(o,t)=>!ae(o,t),Et={attribute:!0,type:String,converter:nt,reflect:!1,useDefault:!1,hasChanged:Ct};Symbol.metadata??=Symbol("metadata"),J.litPropertyMetadata??=new WeakMap;var y=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=Et){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){let i=Symbol(),s=this.getPropertyDescriptor(t,i,e);s!==void 0&&le(this.prototype,t,s)}}static getPropertyDescriptor(t,e,i){let{get:s,set:r}=ce(this.prototype,t)??{get(){return this[e]},set(n){this[e]=n}};return{get:s,set(n){let h=s?.call(this);r?.call(this,n),this.requestUpdate(t,h,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??Et}static _$Ei(){if(this.hasOwnProperty(I("elementProperties")))return;let t=pe(this);t.finalize(),t.l!==void 0&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(I("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(I("properties"))){let e=this.properties,i=[...he(e),...de(e)];for(let s of i)this.createProperty(s,e[s])}let t=this[Symbol.metadata];if(t!==null){let e=litPropertyMetadata.get(t);if(e!==void 0)for(let[i,s]of e)this.elementProperties.set(i,s)}this._$Eh=new Map;for(let[e,i]of this.elementProperties){let s=this._$Eu(e,i);s!==void 0&&this._$Eh.set(s,e)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){let e=[];if(Array.isArray(t)){let i=new Set(t.flat(1/0).reverse());for(let s of i)e.unshift(rt(s))}else t!==void 0&&e.push(rt(t));return e}static _$Eu(t,e){let i=e.attribute;return i===!1?void 0:typeof i=="string"?i:typeof t=="string"?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),this.renderRoot!==void 0&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){let t=new Map,e=this.constructor.elementProperties;for(let i of e.keys())this.hasOwnProperty(i)&&(t.set(i,this[i]),delete this[i]);t.size>0&&(this._$Ep=t)}createRenderRoot(){let t=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return St(t,this.constructor.elementStyles),t}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,i){this._$AK(t,i)}_$ET(t,e){let i=this.constructor.elementProperties.get(t),s=this.constructor._$Eu(t,i);if(s!==void 0&&i.reflect===!0){let r=(i.converter?.toAttribute!==void 0?i.converter:nt).toAttribute(e,i.type);this._$Em=t,r==null?this.removeAttribute(s):this.setAttribute(s,r),this._$Em=null}}_$AK(t,e){let i=this.constructor,s=i._$Eh.get(t);if(s!==void 0&&this._$Em!==s){let r=i.getPropertyOptions(s),n=typeof r.converter=="function"?{fromAttribute:r.converter}:r.converter?.fromAttribute!==void 0?r.converter:nt;this._$Em=s;let h=n.fromAttribute(e,r.type);this[s]=h??this._$Ej?.get(s)??h,this._$Em=null}}requestUpdate(t,e,i,s=!1,r){if(t!==void 0){let n=this.constructor;if(s===!1&&(r=this[t]),i??=n.getPropertyOptions(t),!((i.hasChanged??Ct)(r,e)||i.useDefault&&i.reflect&&r===this._$Ej?.get(t)&&!this.hasAttribute(n._$Eu(t,i))))return;this.C(t,e,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(t,e,{useDefault:i,reflect:s,wrapped:r},n){i&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,n??e??this[t]),r!==!0||n!==void 0)||(this._$AL.has(t)||(this.hasUpdated||i||(e=void 0),this._$AL.set(t,e)),s===!0&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(e){Promise.reject(e)}let t=this.scheduleUpdate();return t!=null&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[s,r]of this._$Ep)this[s]=r;this._$Ep=void 0}let i=this.constructor.elementProperties;if(i.size>0)for(let[s,r]of i){let{wrapped:n}=r,h=this[s];n!==!0||this._$AL.has(s)||h===void 0||this.C(s,void 0,r,h)}}let t=!1,e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(i=>i.hostUpdate?.()),this.update(e)):this._$EM()}catch(i){throw t=!1,this._$EM(),i}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(e=>e.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(e=>this._$ET(e,this[e])),this._$EM()}updated(t){}firstUpdated(t){}};y.elementStyles=[],y.shadowRootOptions={mode:"open"},y[I("elementProperties")]=new Map,y[I("finalized")]=new Map,_e?.({ReactiveElement:y}),(J.reactiveElementVersions??=[]).push("2.1.2");var ut=globalThis,Mt=o=>o,Z=ut.trustedTypes,kt=Z?Z.createPolicy("lit-html",{createHTML:o=>o}):void 0,Ot="$lit$",S=`lit$${Math.random().toFixed(9).slice(2)}$`,Pt="?"+S,me=`<${Pt}>`,k=document,U=()=>k.createComment(""),j=o=>o===null||typeof o!="object"&&typeof o!="function",_t=Array.isArray,fe=o=>_t(o)||typeof o?.[Symbol.iterator]=="function",at=`[ 	
\f\r]`,z=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,Lt=/-->/g,Tt=/>/g,C=RegExp(`>|${at}(?:([^\\s"'>=/]+)(${at}*=${at}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),Nt=/'/g,Rt=/"/g,Ht=/^(?:script|style|textarea|title)$/i,mt=o=>(t,...e)=>({_$litType$:o,strings:t,values:e}),c=mt(1),It=mt(2),zt=mt(3),L=Symbol.for("lit-noChange"),l=Symbol.for("lit-nothing"),Dt=new WeakMap,M=k.createTreeWalker(k,129);function Ut(o,t){if(!_t(o)||!o.hasOwnProperty("raw"))throw Error("invalid template strings array");return kt!==void 0?kt.createHTML(t):t}var ge=(o,t)=>{let e=o.length-1,i=[],s,r=t===2?"<svg>":t===3?"<math>":"",n=z;for(let h=0;h<e;h++){let a=o[h],d,u,p=-1,$=0;for(;$<a.length&&(n.lastIndex=$,u=n.exec(a),u!==null);)$=n.lastIndex,n===z?u[1]==="!--"?n=Lt:u[1]!==void 0?n=Tt:u[2]!==void 0?(Ht.test(u[2])&&(s=RegExp("</"+u[2],"g")),n=C):u[3]!==void 0&&(n=C):n===C?u[0]===">"?(n=s??z,p=-1):u[1]===void 0?p=-2:(p=n.lastIndex-u[2].length,d=u[1],n=u[3]===void 0?C:u[3]==='"'?Rt:Nt):n===Rt||n===Nt?n=C:n===Lt||n===Tt?n=z:(n=C,s=void 0);let b=n===C&&o[h+1].startsWith("/>")?" ":"";r+=n===z?a+me:p>=0?(i.push(d),a.slice(0,p)+Ot+a.slice(p)+S+b):a+S+(p===-2?h:b)}return[Ut(o,r+(o[e]||"<?>")+(t===2?"</svg>":t===3?"</math>":"")),i]},B=class o{constructor({strings:t,_$litType$:e},i){let s;this.parts=[];let r=0,n=0,h=t.length-1,a=this.parts,[d,u]=ge(t,e);if(this.el=o.createElement(d,i),M.currentNode=this.el.content,e===2||e===3){let p=this.el.content.firstChild;p.replaceWith(...p.childNodes)}for(;(s=M.nextNode())!==null&&a.length<h;){if(s.nodeType===1){if(s.hasAttributes())for(let p of s.getAttributeNames())if(p.endsWith(Ot)){let $=u[n++],b=s.getAttribute(p).split(S),K=/([.?@])?(.*)/.exec($);a.push({type:1,index:r,name:K[2],strings:b,ctor:K[1]==="."?ct:K[1]==="?"?ht:K[1]==="@"?dt:R}),s.removeAttribute(p)}else p.startsWith(S)&&(a.push({type:6,index:r}),s.removeAttribute(p));if(Ht.test(s.tagName)){let p=s.textContent.split(S),$=p.length-1;if($>0){s.textContent=Z?Z.emptyScript:"";for(let b=0;b<$;b++)s.append(p[b],U()),M.nextNode(),a.push({type:2,index:++r});s.append(p[$],U())}}}else if(s.nodeType===8)if(s.data===Pt)a.push({type:2,index:r});else{let p=-1;for(;(p=s.data.indexOf(S,p+1))!==-1;)a.push({type:7,index:r}),p+=S.length-1}r++}}static createElement(t,e){let i=k.createElement("template");return i.innerHTML=t,i}};function N(o,t,e=o,i){if(t===L)return t;let s=i!==void 0?e._$Co?.[i]:e._$Cl,r=j(t)?void 0:t._$litDirective$;return s?.constructor!==r&&(s?._$AO?.(!1),r===void 0?s=void 0:(s=new r(o),s._$AT(o,e,i)),i!==void 0?(e._$Co??=[])[i]=s:e._$Cl=s),s!==void 0&&(t=N(o,s._$AS(o,t.values),s,i)),t}var lt=class{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){let{el:{content:e},parts:i}=this._$AD,s=(t?.creationScope??k).importNode(e,!0);M.currentNode=s;let r=M.nextNode(),n=0,h=0,a=i[0];for(;a!==void 0;){if(n===a.index){let d;a.type===2?d=new W(r,r.nextSibling,this,t):a.type===1?d=new a.ctor(r,a.name,a.strings,this,t):a.type===6&&(d=new pt(r,this,t)),this._$AV.push(d),a=i[++h]}n!==a?.index&&(r=M.nextNode(),n++)}return M.currentNode=k,s}p(t){let e=0;for(let i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(t,i,e),e+=i.strings.length-2):i._$AI(t[e])),e++}},W=class o{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,i,s){this.type=2,this._$AH=l,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=i,this.options=s,this._$Cv=s?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode,e=this._$AM;return e!==void 0&&t?.nodeType===11&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=N(this,t,e),j(t)?t===l||t==null||t===""?(this._$AH!==l&&this._$AR(),this._$AH=l):t!==this._$AH&&t!==L&&this._(t):t._$litType$!==void 0?this.$(t):t.nodeType!==void 0?this.T(t):fe(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==l&&j(this._$AH)?this._$AA.nextSibling.data=t:this.T(k.createTextNode(t)),this._$AH=t}$(t){let{values:e,_$litType$:i}=t,s=typeof i=="number"?this._$AC(t):(i.el===void 0&&(i.el=B.createElement(Ut(i.h,i.h[0]),this.options)),i);if(this._$AH?._$AD===s)this._$AH.p(e);else{let r=new lt(s,this),n=r.u(this.options);r.p(e),this.T(n),this._$AH=r}}_$AC(t){let e=Dt.get(t.strings);return e===void 0&&Dt.set(t.strings,e=new B(t)),e}k(t){_t(this._$AH)||(this._$AH=[],this._$AR());let e=this._$AH,i,s=0;for(let r of t)s===e.length?e.push(i=new o(this.O(U()),this.O(U()),this,this.options)):i=e[s],i._$AI(r),s++;s<e.length&&(this._$AR(i&&i._$AB.nextSibling,s),e.length=s)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){let i=Mt(t).nextSibling;Mt(t).remove(),t=i}}setConnected(t){this._$AM===void 0&&(this._$Cv=t,this._$AP?.(t))}},R=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,i,s,r){this.type=1,this._$AH=l,this._$AN=void 0,this.element=t,this.name=e,this._$AM=s,this.options=r,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=l}_$AI(t,e=this,i,s){let r=this.strings,n=!1;if(r===void 0)t=N(this,t,e,0),n=!j(t)||t!==this._$AH&&t!==L,n&&(this._$AH=t);else{let h=t,a,d;for(t=r[0],a=0;a<r.length-1;a++)d=N(this,h[i+a],e,a),d===L&&(d=this._$AH[a]),n||=!j(d)||d!==this._$AH[a],d===l?t=l:t!==l&&(t+=(d??"")+r[a+1]),this._$AH[a]=d}n&&!s&&this.j(t)}j(t){t===l?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}},ct=class extends R{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===l?void 0:t}},ht=class extends R{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==l)}},dt=class extends R{constructor(t,e,i,s,r){super(t,e,i,s,r),this.type=5}_$AI(t,e=this){if((t=N(this,t,e,0)??l)===L)return;let i=this._$AH,s=t===l&&i!==l||t.capture!==i.capture||t.once!==i.once||t.passive!==i.passive,r=t!==l&&(i===l||s);s&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}},pt=class{constructor(t,e,i){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(t){N(this,t)}};var ve=ut.litHtmlPolyfillSupport;ve?.(B,W),(ut.litHtmlVersions??=[]).push("3.3.3");var jt=(o,t,e)=>{let i=e?.renderBefore??t,s=i._$litPart$;if(s===void 0){let r=e?.renderBefore??null;i._$litPart$=s=new W(t.insertBefore(U(),r),r,void 0,e??{})}return s._$AI(o),s};var ft=globalThis,g=class extends y{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){let e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=jt(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return L}};g._$litElement$=!0,g.finalized=!0,ft.litElementHydrateSupport?.({LitElement:g});var $e=ft.litElementPolyfillSupport;$e?.({LitElement:g});(ft.litElementVersions??=[]).push("4.2.2");var Bt={he:{name:"Israel Transit",description:"\u05D6\u05DE\u05E0\u05D9 \u05D4\u05D2\u05E2\u05D4 \u05D1\u05D6\u05DE\u05DF \u05D0\u05DE\u05EA \u05DC\u05EA\u05D7\u05D1\u05D5\u05E8\u05D4 \u05D4\u05E6\u05D9\u05D1\u05D5\u05E8\u05D9\u05EA \u05D1\u05D9\u05E9\u05E8\u05D0\u05DC",scheduled:"\u05DC\u05E4\u05D9 \u05DC\u05D5\u05D7 \u05D6\u05DE\u05E0\u05D9\u05DD",now:"\u05E2\u05DB\u05E9\u05D9\u05D5",minutes:"\u05D3\u05E7\u05F3",minutesLong:"\u05D3\u05E7\u05D5\u05EA",noArrivals:"\u05D0\u05D9\u05DF \u05D4\u05D2\u05E2\u05D5\u05EA \u05E7\u05E8\u05D5\u05D1\u05D5\u05EA",noRealtime:"\u05D0\u05D9\u05DF \u05DB\u05E8\u05D2\u05E2 \u05E0\u05EA\u05D5\u05E0\u05D9 \u05D6\u05DE\u05DF \u05D0\u05DE\u05EA \u05DC\u05EA\u05D7\u05E0\u05D4 \u05D4\u05D6\u05D5",noData:"\u05D0\u05D9\u05DF \u05E0\u05EA\u05D5\u05E0\u05D9\u05DD \u05D6\u05DE\u05D9\u05E0\u05D9\u05DD \u05DC\u05EA\u05D7\u05E0\u05D4 \u05D4\u05D6\u05D5",loading:"\u05D8\u05D5\u05E2\u05DF\u2026",staleData:"\u05D0\u05D9\u05DF \u05D7\u05D9\u05D1\u05D5\u05E8 \u05DB\u05E8\u05D2\u05E2. \u05DE\u05D5\u05E6\u05D2\u05D9\u05DD \u05D4\u05D6\u05DE\u05E0\u05D9\u05DD \u05D4\u05D0\u05D7\u05E8\u05D5\u05E0\u05D9\u05DD \u05E9\u05D4\u05EA\u05E7\u05D1\u05DC\u05D5.",errorUnknownStop:"\u05D4\u05EA\u05D7\u05E0\u05D4 \u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D4. \u05D1\u05D3\u05E7\u05D5 \u05D0\u05EA \u05E7\u05D5\u05D3 \u05D4\u05EA\u05D7\u05E0\u05D4 \u05D1\u05D4\u05D2\u05D3\u05E8\u05D5\u05EA \u05D4\u05DB\u05E8\u05D8\u05D9\u05E1.",errorNotLoaded:"\u05D4\u05D0\u05D9\u05E0\u05D8\u05D2\u05E8\u05E6\u05D9\u05D4 Israel Transit \u05DC\u05D0 \u05E4\u05E2\u05D9\u05DC\u05D4. \u05D1\u05D3\u05E7\u05D5 \u05D0\u05D5\u05EA\u05D4 \u05D1\u05D4\u05D2\u05D3\u05E8\u05D5\u05EA.",errorIndex:"\u05DC\u05D5\u05D7 \u05D4\u05D6\u05DE\u05E0\u05D9\u05DD \u05D4\u05DE\u05E7\u05D5\u05DE\u05D9 \u05E2\u05D3\u05D9\u05D9\u05DF \u05DC\u05D0 \u05DE\u05D5\u05DB\u05DF. \u05E0\u05E1\u05D5 \u05E9\u05D5\u05D1 \u05D1\u05E2\u05D5\u05D3 \u05DB\u05DE\u05D4 \u05D3\u05E7\u05D5\u05EA.",errorConnection:"\u05D4\u05D7\u05D9\u05D1\u05D5\u05E8 \u05DC-Home Assistant \u05D4\u05EA\u05E0\u05EA\u05E7. \u05DE\u05EA\u05D7\u05D1\u05E8 \u05DE\u05D7\u05D3\u05E9\u2026",errorGeneric:"\u05DC\u05D0 \u05E0\u05D9\u05EA\u05DF \u05DC\u05D8\u05E2\u05D5\u05DF \u05DB\u05E8\u05D2\u05E2 \u05D0\u05EA \u05D6\u05DE\u05E0\u05D9 \u05D4\u05D4\u05D2\u05E2\u05D4.",stop:"\u05EA\u05D7\u05E0\u05D4",stopDetails:"\u05E4\u05E8\u05D8\u05D9 \u05D4\u05EA\u05D7\u05E0\u05D4",allLines:"\u05DB\u05DC \u05D4\u05E7\u05D5\u05D5\u05D9\u05DD \u05D1\u05EA\u05D7\u05E0\u05D4",lineDetails:"\u05E4\u05E8\u05D8\u05D9 \u05D4\u05E7\u05D5",routeStops:"\u05EA\u05D7\u05E0\u05D5\u05EA \u05D4\u05E7\u05D5",vehicleHere:"\u05D4\u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E0\u05D5\u05DB\u05D7\u05D9",myStop:"\u05D4\u05EA\u05D7\u05E0\u05D4 \u05E9\u05DC\u05DA",departedAt:"\u05D9\u05E6\u05D0 \u05D1\u05BE",platform:"\u05E8\u05E6\u05D9\u05E3",delay:"\u05E2\u05D9\u05DB\u05D5\u05D1",delayMinutes:"\u05D3\u05E7\u05F3 \u05E2\u05D9\u05DB\u05D5\u05D1",onTime:"\u05D1\u05D6\u05DE\u05DF",operator:"\u05DE\u05E4\u05E2\u05D9\u05DC",destination:"\u05D9\u05E2\u05D3",noLines:"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D5 \u05E7\u05D5\u05D5\u05D9\u05DD \u05D1\u05EA\u05D7\u05E0\u05D4 \u05D4\u05D6\u05D5",noRouteStops:"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0 \u05DE\u05E1\u05DC\u05D5\u05DC \u05DC\u05E7\u05D5 \u05D4\u05D6\u05D4",close:"\u05E1\u05D2\u05D9\u05E8\u05D4",vehicleMap:"\u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E8\u05DB\u05D1",routeLine:"\u05DE\u05E1\u05DC\u05D5\u05DC \u05D4\u05E7\u05D5",noVehicleLocation:"\u05D4\u05DE\u05E4\u05E2\u05D9\u05DC \u05D0\u05D9\u05E0\u05D5 \u05DE\u05E9\u05D3\u05E8 \u05D0\u05EA \u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E8\u05DB\u05D1",editorStop:"\u05EA\u05D7\u05E0\u05D4",editorSearch:"\u05D7\u05D9\u05E4\u05D5\u05E9 \u05EA\u05D7\u05E0\u05D4 \u05DC\u05E4\u05D9 \u05E9\u05DD, \u05E2\u05D9\u05E8, \u05E8\u05D7\u05D5\u05D1 \u05D0\u05D5 \u05E7\u05D5\u05D3",editorSearchHelp:'\u05D0\u05E4\u05E9\u05E8 \u05DC\u05E9\u05DC\u05D1 \u05DE\u05D9\u05DC\u05D9\u05DD, \u05DC\u05DE\u05E9\u05DC "\u05DB\u05E4\u05E8 \u05E1\u05D1\u05D0 \u05D5\u05D9\u05E6\u05DE\u05DF"',editorSearching:"\u05DE\u05D7\u05E4\u05E9\u2026",editorNoResults:"\u05DC\u05D0 \u05E0\u05DE\u05E6\u05D0\u05D5 \u05EA\u05D7\u05E0\u05D5\u05EA",editorLines:"\u05E7\u05D5\u05D5\u05D9\u05DD \u05DC\u05D4\u05E6\u05D2\u05D4",editorLinesHelp:"\u05D1\u05DC\u05D9 \u05D1\u05D7\u05D9\u05E8\u05D4 \u05D9\u05D5\u05E6\u05D2\u05D5 \u05DB\u05DC \u05D4\u05E7\u05D5\u05D5\u05D9\u05DD \u05D1\u05EA\u05D7\u05E0\u05D4",editorAddLine:"\u05D4\u05D5\u05E1\u05E4\u05EA \u05E7\u05D5",editorAllShown:"\u05DB\u05DC \u05D4\u05E7\u05D5\u05D5\u05D9\u05DD \u05D1\u05EA\u05D7\u05E0\u05D4 \u05DB\u05D1\u05E8 \u05D1\u05E8\u05E9\u05D9\u05DE\u05D4",editorMoveUp:"\u05D4\u05E2\u05D1\u05E8\u05D4 \u05DC\u05DE\u05E2\u05DC\u05D4",editorMoveDown:"\u05D4\u05E2\u05D1\u05E8\u05D4 \u05DC\u05DE\u05D8\u05D4",editorRemove:"\u05D4\u05E1\u05E8\u05D4",editorTitle:"\u05DB\u05D5\u05EA\u05E8\u05EA \u05DE\u05D5\u05EA\u05D0\u05DE\u05EA",editorMaxArrivals:"\u05DE\u05E1\u05E4\u05E8 \u05D4\u05D2\u05E2\u05D5\u05EA \u05DE\u05E8\u05D1\u05D9",editorMaxLines:"\u05DE\u05E1\u05E4\u05E8 \u05E7\u05D5\u05D5\u05D9\u05DD \u05DE\u05E8\u05D1\u05D9",editorMaxLinesHelp:"\u200F0 = \u05DC\u05DC\u05D0 \u05D4\u05D2\u05D1\u05DC\u05D4",editorOrder:"\u05E1\u05D3\u05E8 \u05D4\u05D4\u05E6\u05D2\u05D4",editorOrderTime:"\u05DC\u05E4\u05D9 \u05D6\u05DE\u05DF \u05D4\u05D4\u05D2\u05E2\u05D4",editorOrderLines:"\u05DC\u05E4\u05D9 \u05E1\u05D3\u05E8 \u05D4\u05E7\u05D5\u05D5\u05D9\u05DD \u05E9\u05E0\u05D1\u05D7\u05E8",editorDisplay:"\u05E4\u05E8\u05D8\u05D9\u05DD \u05DC\u05D4\u05E6\u05D2\u05D4",editorShowHeader:"\u05DB\u05D5\u05EA\u05E8\u05EA \u05D4\u05EA\u05D7\u05E0\u05D4",editorShowCity:"\u05E9\u05DD \u05D4\u05E2\u05D9\u05E8",editorShowStopCode:"\u05E7\u05D5\u05D3 \u05D4\u05EA\u05D7\u05E0\u05D4",editorShowDestination:"\u05D9\u05E2\u05D3 \u05D4\u05E7\u05D5",editorShowOperator:"\u05E9\u05DD \u05D4\u05DE\u05E4\u05E2\u05D9\u05DC",editorShowModeIcon:"\u05E1\u05DE\u05DC \u05E1\u05D5\u05D2 \u05D4\u05EA\u05D7\u05D1\u05D5\u05E8\u05D4",editorShowRealtimeTag:'\u05EA\u05D5\u05D5\u05D9\u05EA "\u05DC\u05E4\u05D9 \u05DC\u05D5\u05D7 \u05D6\u05DE\u05E0\u05D9\u05DD"',editorShowPlatform:"\u05E8\u05E6\u05D9\u05E3",editorShowDelay:"\u05E2\u05D9\u05DB\u05D5\u05D1",editorShowClock:"\u05E9\u05E2\u05EA \u05D4\u05D2\u05E2\u05D4 \u05DE\u05D3\u05D5\u05D9\u05E7\u05EA",editorShowMap:"\u05DE\u05E4\u05D4 \u05E2\u05DD \u05DE\u05D9\u05E7\u05D5\u05DD \u05D4\u05E8\u05DB\u05D1",editorShowMapHelp:"\u05E0\u05E4\u05EA\u05D7\u05EA \u05D1\u05E4\u05E8\u05D8\u05D9 \u05D4\u05E7\u05D5, \u05DB\u05E9\u05D4\u05DE\u05E4\u05E2\u05D9\u05DC \u05DE\u05E9\u05D3\u05E8 \u05DE\u05D9\u05E7\u05D5\u05DD",editorChange:"\u05E9\u05D9\u05E0\u05D5\u05D9 \u05EA\u05D7\u05E0\u05D4",editorCancel:"\u05D1\u05D9\u05D8\u05D5\u05DC",editorNoStop:"\u05DC\u05D0 \u05E0\u05D1\u05D7\u05E8\u05D4 \u05EA\u05D7\u05E0\u05D4",errorNoStop:"\u05D9\u05E9 \u05DC\u05D4\u05D2\u05D3\u05D9\u05E8 \u05E7\u05D5\u05D3 \u05EA\u05D7\u05E0\u05D4 (stop_code)",mode_0:"\u05E8\u05DB\u05D1\u05EA \u05E7\u05DC\u05D4",mode_2:"\u05E8\u05DB\u05D1\u05EA \u05D9\u05E9\u05E8\u05D0\u05DC",mode_3:"\u05D0\u05D5\u05D8\u05D5\u05D1\u05D5\u05E1",mode_5:"\u05E8\u05DB\u05D1\u05DC\u05D9\u05EA",mode_8:"\u05DE\u05D5\u05E0\u05D9\u05EA \u05E9\u05D9\u05E8\u05D5\u05EA",mode_715:"\u05E7\u05D5 \u05D2\u05DE\u05D9\u05E9"},en:{name:"Israel Transit",description:"Real-time Israeli public transport arrivals",scheduled:"Timetable",now:"Now",minutes:"min",minutesLong:"minutes",noArrivals:"No upcoming arrivals",noRealtime:"No real-time data for this stop right now",noData:"No data is published for this stop",loading:"Loading\u2026",staleData:"Offline right now. Showing the last times received.",errorUnknownStop:"Stop not found. Check the stop code in the card's settings.",errorNotLoaded:"The Israel Transit integration is not running. Check it in Settings.",errorIndex:"The local timetable is not ready yet. Try again in a few minutes.",errorConnection:"Lost the connection to Home Assistant. Reconnecting\u2026",errorGeneric:"Could not load arrival times right now.",stop:"Stop",stopDetails:"Stop details",allLines:"All lines at this stop",lineDetails:"Line details",routeStops:"Stops on this route",vehicleHere:"Current position",myStop:"Your stop",departedAt:"Departed at",platform:"Platform",delay:"Delay",delayMinutes:"min late",onTime:"On time",operator:"Operator",destination:"Destination",noLines:"No lines found at this stop",noRouteStops:"No route found for this line",close:"Close",vehicleMap:"Vehicle position",routeLine:"Route",noVehicleLocation:"The operator is not broadcasting this vehicle's position",editorStop:"Stop",editorSearch:"Search by stop name, city, street or code",editorSearchHelp:'Words combine, for example "Kfar Saba Weizmann"',editorSearching:"Searching\u2026",editorNoResults:"No stops found",editorLines:"Lines to show",editorLinesHelp:"With nothing chosen, every line at the stop is shown",editorAddLine:"Add a line",editorAllShown:"Every line at this stop is already listed",editorMoveUp:"Move up",editorMoveDown:"Move down",editorRemove:"Remove",editorTitle:"Custom title",editorMaxArrivals:"Maximum arrivals",editorMaxLines:"Maximum lines",editorMaxLinesHelp:"0 = no limit",editorOrder:"Order",editorOrderTime:"By arrival time",editorOrderLines:"By the chosen line order",editorDisplay:"Details to show",editorShowHeader:"Stop header",editorShowCity:"City",editorShowStopCode:"Stop code",editorShowDestination:"Destination",editorShowOperator:"Operator name",editorShowModeIcon:"Mode icon",editorShowRealtimeTag:"Timetable tag",editorShowPlatform:"Platform",editorShowDelay:"Delay",editorShowClock:"Exact arrival time",editorShowMap:"Map with the vehicle position",editorShowMapHelp:"Opens in the line details, when a position is broadcast",editorChange:"Change stop",editorCancel:"Cancel",editorNoStop:"No stop selected",errorNoStop:"You need to define a stop_code",mode_0:"Light rail",mode_2:"Train",mode_3:"Bus",mode_5:"Cable car",mode_8:"Shared taxi",mode_715:"Flexible route"}},ye=o=>(o?.locale?.language||o?.language||"he").toLowerCase().startsWith("he")?"he":"en",f=(o,t)=>{let e=ye(o);return Bt[e][t]??Bt.en[t]??t};var v="israel_transit",Wt="israel-transit-dialog-closed",Vt=`/${v}/brand/icon.png`,gt={0:"mdi:tram",2:"mdi:train",3:"mdi:bus",5:"mdi:gondola",8:"mdi:taxi",715:"mdi:bus-clock"},vt={0:"#7b4fd1",2:"#1e6fbf",3:"#2f7d4f",5:"#b5651d",8:"#a3892c",715:"#4a6572"},$t="#03a9f4",Q="#db4437",yt="#f0a202",tt=o=>gt[o]??"mdi:bus",T=o=>o!=null&&gt[o]?`var(--it-mode-${o})`:"var(--it-mode-unknown)",qt=o=>vt[o]??$t,bt=(o,t)=>t!=null&&gt[t]?f(o,`mode_${t}`):"",Gt=(o,t=Date.now())=>{let e=Date.parse(o);return Number.isNaN(e)?null:Math.max(0,Math.floor((e-t)/6e4))},be=o=>{if(!o)return!1;if(o.time_format==="12")return!0;if(o.time_format==="24")return!1;let t=o.time_format==="system"?void 0:o.language;return new Date("January 1, 2023 22:00:00").toLocaleString(t).includes("10")},V=(o,t)=>{let e=new Date(o);if(Number.isNaN(e.getTime()))return"";let i=t?.locale;try{return new Intl.DateTimeFormat(i?.language||"he-IL",{hour:"2-digit",minute:"2-digit",hourCycle:be(i)?"h12":"h23",timeZone:i?.time_zone==="server"?t?.config?.time_zone:void 0}).format(e)}catch{return e.toTimeString().slice(0,5)}},xe={unknown_stop:"errorUnknownStop",unknown_command:"errorNotLoaded",search_failed:"errorIndex",lookup_failed:"errorIndex",3:"errorConnection"},q=(o,t)=>{let e=t?.code??t?.error?.code,i=xe[e];return i?f(o,i):f(o,"errorGeneric")},Ft=()=>customElements.get("ha-adaptive-dialog")?"ha-adaptive-dialog":"ha-dialog",Kt=(o,t,e={})=>{let i=new CustomEvent(t,{detail:e,bubbles:!0,composed:!0});return o.dispatchEvent(i),i},Xt=async()=>{if(customElements.get("ha-map"))return!0;try{await(await window.loadCardHelpers?.())?.createCardElement({type:"map",entities:["zone.home"]})}catch{}return!!customElements.get("ha-map")};var we=x(Object.entries(vt).map(([o,t])=>`--it-mode-${o}: ${t};`).join(`
    `)+`
    --it-mode-unknown: var(--primary-color, ${$t});`),D=w`
  :host {
    ${we}
    --it-gap: 12px;
    --it-radius: 12px;
    display: block;
  }

  .badge {
    flex: 0 0 auto;
    min-width: 44px;
    padding: 4px 8px;
    border-radius: 8px;
    background: var(--it-badge-color, var(--it-mode-unknown));
    color: #fff;
    font-weight: 700;
    font-size: 1rem;
    line-height: 1.25;
    text-align: center;
    font-variant-numeric: tabular-nums;
    /* Line numbers stay left-to-right even inside an RTL layout. */
    direction: ltr;
    unicode-bidi: isolate;
  }

  .tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.75rem;
    line-height: 1.3;
    white-space: nowrap;
  }

  .tag.timetable {
    color: var(--secondary-text-color);
  }


  .muted {
    color: var(--secondary-text-color);
  }

  .empty {
    padding: 24px 16px;
    text-align: center;
    color: var(--secondary-text-color);
  }

  .error {
    padding: 12px 16px;
    color: var(--error-color, #db4437);
  }
`,Yt=w`
  ha-card {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
    container-type: inline-size;
  }

  .header {
    display: flex;
    align-items: flex-start;
    gap: var(--it-gap);
    padding: 16px 16px 12px;
    cursor: pointer;
    border: none;
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    width: 100%;
  }

  .header:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }

  .titles {
    flex: 1 1 auto;
    min-width: 0;
  }

  .stop-name {
    font-size: 1.25rem;
    font-weight: 500;
    line-height: 1.3;
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .stop-meta {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-block-start: 2px;
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
  }

  .code {
    padding: 1px 6px;
    border-radius: 6px;
    background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.16));
    font-variant-numeric: tabular-nums;
    direction: ltr;
    unicode-bidi: isolate;
  }

  /* Over a board that is still shown: the times are real, just not fresh. */
  .stale {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 16px;
    font-size: 0.75rem;
    color: var(--warning-color, #ffa600);
    --mdc-icon-size: 16px;
  }

  .rows {
    display: flex;
    flex-direction: column;
    flex: 1 1 auto;
    overflow-y: auto;
  }

  .row {
    display: flex;
    align-items: center;
    gap: var(--it-gap);
    padding: 10px 16px;
    border: none;
    border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
    background: none;
    color: inherit;
    font: inherit;
    text-align: start;
    width: 100%;
    cursor: pointer;
  }

  .row:hover {
    background: var(--ha-color-surface-lower, rgba(127, 127, 127, 0.08));
  }

  .row:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: -2px;
  }

  .row-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .destination {
    font-size: 0.9375rem;
    color: var(--primary-text-color);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .sub {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 2px 6px;
    margin-block-start: 2px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }

  .sep {
    color: var(--secondary-text-color);
  }

  .eta {
    flex: 0 0 auto;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 52px;
    line-height: 1.1;
  }

  .eta-value {
    font-size: 1.5rem;
    font-weight: 500;
    color: var(--primary-text-color);
    font-variant-numeric: tabular-nums;
  }

  .eta-unit {
    font-size: 0.6875rem;
    color: var(--secondary-text-color);
  }

  .eta-now .eta-value {
    font-size: 1.0625rem;
    color: var(--success-color, #43a047);
  }

  .eta-clock {
    font-size: 1.0625rem;
  }

  .at-clock {
    font-size: 0.6875rem;
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
    direction: ltr;
    unicode-bidi: isolate;
  }

  .mode {
    flex: 0 0 auto;
    --mdc-icon-size: 20px;
    color: var(--secondary-text-color);
  }

  .delay {
    font-size: 0.6875rem;
    font-weight: 500;
    color: var(--warning-color, #ffa600);
    font-variant-numeric: tabular-nums;
    /* Keep "+4" from being reordered to "4+" inside an RTL line. */
    direction: ltr;
    unicode-bidi: isolate;
  }

  /* Genuinely narrow dashboard columns: drop to the essentials. A
     full-width card on a small phone is ~327px, and should keep everything. */
  @container (max-width: 290px) {
    .header,
    .row {
      padding-inline: 12px;
    }
    .sub .operator,
    /* and the separator it would otherwise leave stranded */
    .sub .operator + .sep,
    .mode {
      display: none;
    }
    .eta {
      min-width: 44px;
    }
    .eta-value {
      font-size: 1.25rem;
    }
  }
`;var Se=3e4,Ae=1e4,Ee=6e4,A={max_arrivals:6,max_lines:0,order:"time",show_header:!0,show_city:!0,show_stop_code:!0,show_destination:!0,show_operator:!0,show_mode_icon:!1,show_realtime_tag:!0,show_platform:!0,show_delay:!0,show_clock:!1,show_map:!0},O=class extends g{constructor(){super();m(this,"_onReconnect",()=>this._refresh());this._data=null,this._error=null,this._tick=0,this._stopDialog=!1,this._routeDialog=null}set hass(e){let i=!this._hass;this._hass=e,e?.connection!==this._connection&&this._watch(e?.connection),i&&this._refresh()}get hass(){return this._hass}static getConfigElement(){return document.createElement("israel-transit-card-editor")}static getStubConfig(e){return{stop_code:Object.values(e?.states||{}).find(s=>s.attributes?.stop_code)?.attributes.stop_code??null,max_arrivals:A.max_arrivals}}setConfig(e){if(!e||typeof e!="object")throw new Error(f(this.hass,"errorNoStop"));this._config={...A,...e},this._data=null,this._error=null,this._refresh()}getCardSize(){return(this._config?.max_arrivals??A.max_arrivals)+2}getGridOptions(){let e=Math.min(this._config?.max_arrivals??A.max_arrivals,8),i=this._config?.show_header===!1?1:2;return{rows:e+i,columns:12,min_rows:3,min_columns:6}}connectedCallback(){super.connectedCallback(),this._startTimers(),this._onVisibility=()=>{document.visibilityState==="visible"?(this._startTimers(),this._refresh()):this._stopTimers()},document.addEventListener("visibilitychange",this._onVisibility),this._connection?.addEventListener("ready",this._onReconnect),this._refresh()}disconnectedCallback(){super.disconnectedCallback(),this._stopTimers(),document.removeEventListener("visibilitychange",this._onVisibility),this._connection?.removeEventListener("ready",this._onReconnect)}_watch(e){this._connection?.removeEventListener("ready",this._onReconnect),this._connection=e,this.isConnected&&e?.addEventListener("ready",this._onReconnect)}_startTimers(){this._stopTimers(),document.visibilityState!=="hidden"&&(this._refreshTimer=setInterval(()=>this._refresh(),Se),this._tickTimer=setInterval(()=>{this._tick=Date.now()},Ae))}_stopTimers(){clearInterval(this._refreshTimer),clearInterval(this._tickTimer),this._refreshTimer=void 0,this._tickTimer=void 0}async _refresh(){if(!this.hass||!this._config?.stop_code)return;let e=Number(this._config.stop_code);try{let i=await this.hass.callWS({type:`${v}/stop`,stop_code:e,rail_destination:this._config.rail_destination||null});if(e!==Number(this._config?.stop_code))return;this._data=i,this._error=null,this._followVehicle()}catch(i){if(e!==Number(this._config?.stop_code))return;this._error=q(this.hass,i)}}_followVehicle(){let e=this._routeDialog;if(!e)return;let i=this._data?.arrivals||[],s=e.vehicle_ref?i.find(r=>r.vehicle_ref===e.vehicle_ref):i.find(r=>r.line_ref===e.line_ref);s&&(this._routeDialog=s)}_t(e){return f(this.hass,e)}get _arrivals(){let e=this._config,i=Date.now()-Ee,s=(this._data?.arrivals||[]).filter(a=>!(Date.parse(a.eta)<i)),r=(e.lines||[]).map(String),n=r.length?s.filter(a=>r.includes(String(a.line_name))):s;e.order==="lines"&&r.length&&(n=[...n].sort((a,d)=>r.indexOf(String(a.line_name))-r.indexOf(String(d.line_name))));let h=Number(e.max_lines)||0;if(h>0){let a=new Set;n=n.filter(d=>{let u=String(d.line_name);return a.has(u)?!0:a.size>=h?!1:(a.add(u),!0)})}return n.slice(0,e.max_arrivals??A.max_arrivals)}render(){if(!this._config)return l;if(!this._config.stop_code)return c`<ha-card
        ><div class="empty">${this._t("editorNoStop")}</div></ha-card
      >`;let e=this._data?.stop;this._tick;let i=this._data?this._arrivals:[];return c`
      <ha-card>
        ${this._config.show_header===!1?l:this._renderHeader(e)}
        ${this._error&&this._data?c`<div class="stale" role="status">
              <ha-icon icon="mdi:cloud-alert-outline"></ha-icon>
              <span>${this._t("staleData")}</span>
            </div>`:l}
        <div class="rows">
          ${this._data?i.length===0?c`<div class="empty">${this._emptyMessage()}</div>`:i.map(s=>this._renderRow(s)):this._error?c`<div class="error" role="alert">${this._error}</div>`:c`<div class="empty">${this._t("loading")}</div>`}
        </div>
        ${this._renderDialogs(e)}
      </ha-card>
    `}_emptyMessage(){return this._config.lines?.length?this._t("noArrivals"):this._data.realtime_error&&!this._data.routes?.length?this._t("noData"):this._data.realtime_error?this._t("noRealtime"):this._t("noArrivals")}_renderHeader(e){let i=this._config.title||e?.name||this._t("loading"),s=this._config.show_city!==!1&&e?.city,r=this._config.show_stop_code!==!1&&e?.code;return c`
      <button
        class="header"
        part="header"
        @click=${()=>this._stopDialog=!0}
        aria-label=${this._t("stopDetails")}
      >
        <div class="titles">
          <div class="stop-name">${i}</div>
          ${s||r?c`<div class="stop-meta">
                ${s?c`<span>${e.city}</span>`:l}
                ${r?c`<span class="code">${e.code}</span>`:l}
              </div>`:l}
        </div>
        <ha-icon class="muted" icon="mdi:information-outline"></ha-icon>
      </button>
    `}_renderRow(e){let i=this._config,s=Gt(e.eta),r=s===null||s>59,n=V(e.eta,this.hass);return c`
      <button class="row" @click=${()=>this._routeDialog=e}>
        ${i.show_mode_icon?c`<ha-icon
              class="mode"
              .icon=${tt(e.route_type)}
            ></ha-icon>`:l}
        <div
          class="badge"
          style=${`--it-badge-color:${T(e.route_type)}`}
        >
          ${e.line_name}
        </div>
        <div class="row-body">
          ${i.show_destination!==!1?c`<div class="destination">
                ${e.destination||e.line_name}
              </div>`:l}
          ${this._renderSub(e)}
        </div>
        <div class="eta ${s===0?"eta-now":""}">
          ${r?c`<span class="eta-value eta-clock">${n}</span>`:s===0?c`<span class="eta-value">${this._t("now")}</span>`:c`<span class="eta-value">${s}</span>
                  <span class="eta-unit">${this._t("minutes")}</span>`}
          ${i.show_clock&&!r?c`<span class="at-clock">${n}</span>`:l}
          ${i.show_delay!==!1&&e.delay_minutes?c`<span class="delay">+${e.delay_minutes}</span>`:l}
        </div>
      </button>
    `}_renderSub(e){let i=this._config,s=[i.show_operator!==!1&&e.operator?c`<span class="operator">${e.operator}</span>`:l,i.show_realtime_tag!==!1&&!e.is_realtime?c`<span class="tag timetable"
            ><ha-icon
              icon="mdi:calendar-clock"
              style="--mdc-icon-size:13px"
            ></ha-icon
            >${this._t("scheduled")}</span
          >`:l,i.show_platform!==!1&&e.platform?c`<span>${this._t("platform")} ${e.platform}</span>`:l].filter(r=>r!==l);return s.length?c`<div class="sub">
      ${s.map((r,n)=>n?c`<span class="sep">·</span>${r}`:r)}
    </div>`:l}_renderDialogs(e){return c`
      ${this._stopDialog?c`<israel-transit-stop-dialog
            .hass=${this.hass}
            .stop=${e}
            .open=${!0}
            @israel-transit-dialog-closed=${()=>this._stopDialog=!1}
          ></israel-transit-stop-dialog>`:l}
      ${this._routeDialog?c`<israel-transit-route-dialog
            .hass=${this.hass}
            .arrival=${this._routeDialog}
            .stopCode=${e?.code??this._config.stop_code}
            .showMap=${this._config.show_map!==!1}
            .open=${!0}
            @israel-transit-dialog-closed=${()=>this._routeDialog=null}
          ></israel-transit-route-dialog>`:l}
    `}};m(O,"properties",{_config:{state:!0},_data:{state:!0},_error:{state:!0},_tick:{state:!0},_stopDialog:{state:!0},_routeDialog:{state:!0}}),m(O,"styles",[D,Yt]);var Ce=300,Me=o=>Object.fromEntries(Object.entries(o).filter(([t,e])=>e!=null&&e!==""&&!(Array.isArray(e)&&e.length===0)&&A[t]!==e)),P=class extends g{constructor(){super();m(this,"_computeLabel",e=>({title:this._t("editorTitle"),max_arrivals:this._t("editorMaxArrivals"),max_lines:this._t("editorMaxLines"),order:this._t("editorOrder"),show_header:this._t("editorShowHeader"),show_city:this._t("editorShowCity"),show_stop_code:this._t("editorShowStopCode"),show_destination:this._t("editorShowDestination"),show_operator:this._t("editorShowOperator"),show_mode_icon:this._t("editorShowModeIcon"),show_realtime_tag:this._t("editorShowRealtimeTag"),show_platform:this._t("editorShowPlatform"),show_delay:this._t("editorShowDelay"),show_clock:this._t("editorShowClock"),show_map:this._t("editorShowMap"),rail_destination:this._t("mode_2")})[e.name]??e.name);m(this,"_computeHelper",e=>({max_lines:this._t("editorMaxLinesHelp"),show_map:this._t("editorShowMapHelp")})[e.name]);this._results=[],this._routes=[],this._searching=!1,this._searched=!1,this._picking=!1}connectedCallback(){super.connectedCallback(),this._config?.stop_code&&!this._stop&&this._loadStop()}disconnectedCallback(){super.disconnectedCallback(),clearTimeout(this._searchTimer)}updated(e){e.has("hass")&&!e.get("hass")&&!this._stop&&this._loadStop()}setConfig(e){this._config={...e},e.stop_code&&Number(this._stop?.code)!==Number(e.stop_code)&&this._loadStop()}_t(e){return f(this.hass,e)}async _loadStop(){if(!this.hass||!this._config?.stop_code)return;let e=Number(this._config.stop_code);try{let[i,s]=await Promise.all([this.hass.callWS({type:`${v}/stop`,stop_code:e}),this.hass.callWS({type:`${v}/stop_routes`,stop_code:e})]);if(e!==Number(this._config?.stop_code))return;this._stop=i.stop,this._routes=s}catch{if(e!==Number(this._config?.stop_code))return;this._stop={code:e,name:""},this._routes=[]}}_onSearchInput(e){if(this._query=e.target.value??"",clearTimeout(this._searchTimer),this._query.trim().length<2){this._results=[],this._searched=!1;return}let i=this._query.trim();this._searchTimer=setTimeout(()=>this._search(i),Ce)}async _search(e){if(!this.hass)return;let i=this._searchSeq=(this._searchSeq||0)+1;this._searching=!0;let s=[];try{s=await this.hass.callWS({type:`${v}/search_stops`,query:e,limit:30})}catch{s=[]}i===this._searchSeq&&(this._results=s,this._searching=!1,this._searched=!0)}_pick(e){this._stop=e,this._close(),this._emit({...this._config,stop_code:e.code,lines:[]}),this._loadRoutes(e.code)}_close(){this._results=[],this._searched=!1,this._picking=!1,this._query=""}async _loadRoutes(e){try{this._routes=await this.hass.callWS({type:`${v}/stop_routes`,stop_code:Number(e)})}catch{this._routes=[]}}get _routesByLine(){let e=new Map;for(let i of this._routes){let s=String(i.line_name);e.has(s)||e.set(s,i)}return e}get _lines(){return(this._config?.lines||[]).map(String)}_setLines(e){this._emit({...this._config,lines:e})}_move(e,i){let s=[...this._lines],r=e+i;r<0||r>=s.length||([s[e],s[r]]=[s[r],s[e]],this._emit({...this._config,lines:s,order:"lines"}))}_removeLine(e){this._setLines(this._lines.filter((i,s)=>s!==e))}_addLine(e){this._setLines([...this._lines,e])}_onFormChange(e){e.stopPropagation(),this._emit({...this._config,...e.detail.value})}_emit(e){this._config=Me(e),Kt(this,"config-changed",{config:this._config})}get _schema(){let e=this._routes.some(s=>s.route_type==="2"),i=["show_header","show_city","show_stop_code","show_destination","show_operator","show_mode_icon","show_realtime_tag","show_platform","show_delay","show_clock"];return[{name:"title",selector:{text:{}}},{name:"",type:"grid",schema:[{name:"max_arrivals",selector:{number:{min:1,max:20,step:1,mode:"box"}}},{name:"max_lines",selector:{number:{min:0,max:20,step:1,mode:"box"}}}]},...this._lines.length?[{name:"order",selector:{select:{mode:"dropdown",options:[{value:"time",label:this._t("editorOrderTime")},{value:"lines",label:this._t("editorOrderLines")}]}}}]:[],{name:"",type:"expandable",title:this._t("editorDisplay"),icon:"mdi:eye-settings-outline",schema:[{name:"",type:"grid",schema:i.map(s=>({name:s,selector:{boolean:{}}}))},{name:"show_map",selector:{boolean:{}}}]},...e?[{name:"rail_destination",selector:{text:{}}}]:[]]}render(){if(!this._config||!this.hass)return l;let e=!this._config.stop_code||this._picking;return c`
      <div class="box">
        <div class="brand">
          <img src=${Vt} alt="" aria-hidden="true" />
          <span class="brand-name">${this._t("name")}</span>
        </div>
        ${e?this._renderSearch():this._renderSelected()}
        ${this._config.stop_code?c`
              ${this._renderLines()}
              <ha-form
                .hass=${this.hass}
                .data=${{...A,...this._config}}
                .schema=${this._schema}
                .computeLabel=${this._computeLabel}
                .computeHelper=${this._computeHelper}
                @value-changed=${this._onFormChange}
              ></ha-form>
            `:l}
      </div>
    `}_renderSelected(){let e=this._stop||{code:this._config.stop_code};return c`
      <div class="selected">
        <ha-icon icon="mdi:bus-stop"></ha-icon>
        <div class="selected-body">
          <div class="selected-name">${e.name||this._t("stop")}</div>
          <div class="selected-sub">
            ${[e.street,e.city,e.code].filter(Boolean).join(" \xB7 ")}
          </div>
        </div>
        <button class="chip" @click=${()=>this._picking=!0}>
          ${this._t("editorChange")}
        </button>
      </div>
    `}_renderSearch(){return c`
      <div class="field">
        <div class="row">
          <label for="it-search">${this._t("editorSearch")}</label>
          ${this._config.stop_code?c`<button
                class="tool"
                title=${this._t("editorCancel")}
                aria-label=${this._t("editorCancel")}
                @click=${this._close}
              >
                <ha-icon icon="mdi:close"></ha-icon>
              </button>`:l}
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
      ${this._searching?c`<div class="hint">${this._t("editorSearching")}</div>`:this._results.length?c`<div class="results">
              ${this._results.map(e=>c`
                  <button class="result" @click=${()=>this._pick(e)}>
                    <div class="result-name">${e.name}</div>
                    <div class="result-sub">
                      ${[e.street,e.city,e.code].filter(Boolean).join(" \xB7 ")}
                    </div>
                  </button>
                `)}
            </div>`:this._searched?c`<div class="hint">${this._t("editorNoResults")}</div>`:l}
    `}_renderLines(){let e=this._routesByLine,i=this._lines,s=[...e.keys()].filter(r=>!i.includes(r));return c`
      <div class="section">
        <div class="section-title">${this._t("editorLines")}</div>
        ${i.length?i.map((r,n)=>this._renderChosenLine(r,n,i.length,e.get(r))):c`<div class="hint">${this._t("editorLinesHelp")}</div>`}
        ${s.length?c`<div class="chips">
              ${s.map(r=>this._renderAddChip(r,e.get(r)))}
            </div>`:e.size?c`<div class="hint">${this._t("editorAllShown")}</div>`:l}
      </div>
    `}_renderChosenLine(e,i,s,r){return c`
      <div class="line">
        <div
          class="badge"
          style=${`--it-badge-color:${T(r?.route_type)}`}
        >
          ${e}
        </div>
        <div class="line-body">
          <div class="line-sub">
            ${[r?.destination,r?.operator].filter(Boolean).join(" \xB7 ")}
          </div>
        </div>
        <div class="tools">
          <button
            class="tool"
            ?disabled=${i===0}
            title=${this._t("editorMoveUp")}
            aria-label=${this._t("editorMoveUp")}
            @click=${()=>this._move(i,-1)}
          >
            <ha-icon icon="mdi:arrow-up"></ha-icon>
          </button>
          <button
            class="tool"
            ?disabled=${i===s-1}
            title=${this._t("editorMoveDown")}
            aria-label=${this._t("editorMoveDown")}
            @click=${()=>this._move(i,1)}
          >
            <ha-icon icon="mdi:arrow-down"></ha-icon>
          </button>
          <button
            class="tool"
            title=${this._t("editorRemove")}
            aria-label=${this._t("editorRemove")}
            @click=${()=>this._removeLine(i)}
          >
            <ha-icon icon="mdi:close"></ha-icon>
          </button>
        </div>
      </div>
    `}_renderAddChip(e,i){return c`
      <button
        class="chip"
        style=${`--it-badge-color:${T(i?.route_type)}`}
        title=${`${this._t("editorAddLine")}: ${e}`}
        @click=${()=>this._addLine(e)}
      >
        <span class="swatch"></span>
        <span class="line-name">${e}</span>
      </button>
    `}};m(P,"properties",{hass:{attribute:!1},_config:{state:!0},_stop:{state:!0},_routes:{state:!0},_results:{state:!0},_searching:{state:!0},_searched:{state:!0},_picking:{state:!0}}),m(P,"styles",[D,w`
      .box {
        display: flex;
        flex-direction: column;
        gap: 16px;
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
        width: 32px;
        height: 32px;
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

      .tool ha-icon {
        --mdc-icon-size: 20px;
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
    `]);var Zt=Symbol.for(""),ke=o=>{if(o?.r===Zt)return o?._$litStatic$},Qt=o=>({_$litStatic$:o,r:Zt});var Jt=new Map,xt=o=>(t,...e)=>{let i=e.length,s,r,n=[],h=[],a,d=0,u=!1;for(;d<i;){for(a=t[d];d<i&&(r=e[d],(s=ke(r))!==void 0);)a+=s+t[++d],u=!0;d!==i&&h.push(r),n.push(a),d++}if(d===i&&n.push(t[i]),u){let p=n.join("$$lit$$");(t=Jt.get(p))===void 0&&(n.raw=n,Jt.set(p,t=n)),e=h}return o(t,...e)},_=xt(c),Ei=xt(It),Ci=xt(zt);var Le=6,Te=12,te=16,Ne=40,Re=50,ee=16,De=.045,Oe=25,Pe=220,He=111320,Ie=(o,t)=>{let e=o?new Date(o):null;return e&&!Number.isNaN(e.getTime())?e:t},it=o=>o.lat!=null&&o.lon!=null,et=o=>[o.lat,o.lon],se=(o,t,e,i)=>{let s=h=>h*Math.PI/180,r=s(e-o),n=s(i-t)*Math.cos(s((o+e)/2));return 6371e3*Math.sqrt(r*r+n*n)},ze=(o,t,e)=>{if(t==null||e==null)return-1;let i=-1,s=1/0;return o.forEach((r,n)=>{if(!it(r))return;let h=se(t,e,r.lat,r.lon);h<s&&(s=h,i=n)}),s<=2e3?i:-1},Ue=o=>{if(o.length<2)return 0;let t=o.map(i=>i[0]),e=o.map(i=>i[1]);return se(Math.min(...t),Math.min(...e),Math.max(...t),Math.max(...e))},je=o=>Math.min(Pe,Math.max(Oe,Ue(o)*De)),ie=(o,t,e,i,s)=>{let[r,n]=o,h=t/He,a=h/Math.max(.2,Math.cos(r*Math.PI/180));return{points:Array.from({length:ee+1},(d,u)=>{let p=u/ee*2*Math.PI;return{point:[r+h*Math.sin(p),n+a*Math.cos(p)],timestamp:s}}),color:e,name:i}},Be=w`
  .list {
    display: flex;
    flex-direction: column;
  }

  .item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 2px;
    border-top: 1px solid var(--divider-color, rgba(127, 127, 127, 0.2));
  }

  .item:first-child {
    border-top: none;
  }

  .item-body {
    flex: 1 1 auto;
    min-width: 0;
  }

  .item-title {
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .item-sub {
    margin-block-start: 2px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }

  .stop {
    display: grid;
    grid-template-columns: 20px 1fr auto;
    align-items: center;
    gap: 12px;
    padding-block: 8px;
  }

  .track {
    position: relative;
    align-self: stretch;
    display: flex;
    justify-content: center;
    align-items: center;
  }

  .track::before {
    content: "";
    position: absolute;
    inset-block: -8px;
    width: 2px;
    background: var(--divider-color, rgba(127, 127, 127, 0.35));
  }

  .stop:first-child .track::before {
    inset-block-start: 50%;
  }

  .stop:last-child .track::before {
    inset-block-end: 50%;
  }

  .node {
    position: relative;
    width: 11px;
    height: 11px;
    border-radius: 50%;
    background: var(--card-background-color, #fff);
    border: 2px solid var(--divider-color, rgba(127, 127, 127, 0.6));
  }

  /* The same two colours the map paints these with, so the list and the map
     can be read as one picture. */
  .stop.mine .node {
    width: 15px;
    height: 15px;
    border-color: ${x(yt)};
  }

  .stop.here .node {
    width: 15px;
    height: 15px;
    background: ${x(Q)};
    border-color: ${x(Q)};
  }

  .stop.here .stop-title,
  .stop.mine .stop-title {
    font-weight: 600;
  }

  .stop-title {
    color: var(--primary-text-color);
    overflow-wrap: anywhere;
  }

  .stop-sub {
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }

  .time {
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
    font-variant-numeric: tabular-nums;
  }

  .note {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-block-end: 12px;
    padding: 10px 12px;
    border-radius: 10px;
    background: var(--ha-color-surface-low, rgba(127, 127, 127, 0.12));
    font-size: 0.8125rem;
    color: var(--secondary-text-color);
  }

  ha-icon {
    --mdc-icon-size: 20px;
    flex: 0 0 auto;
  }

  ha-map {
    height: 230px;
    border-radius: var(--ha-card-border-radius, 12px);
    overflow: hidden;
  }

  /* Says what each colour on the map means, which is cheaper than a marker
     the map API has no way to label. */
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 14px;
    margin-block: 8px 12px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }

  .key {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .key i {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex: 0 0 auto;
  }

  /* A bottom sheet on a phone has far less room than a desktop dialog. */
  @media (max-height: 640px) {
    ha-map {
      height: 165px;
    }
  }
`,E=class extends g{constructor(){super(),this.open=!1,this._loading=!1,this._error=null}set hass(t){this._hass=t}get hass(){return this._hass}get _dialog(){return this.__dialog??=Qt(Ft()),this.__dialog}_t(t){return f(this.hass,t)}_closed(){this.open=!1,this.dispatchEvent(new CustomEvent(Wt))}_renderState(t,e){return this._loading?_`<div class="empty">${this._t("loading")}</div>`:this._error?_`<div class="error">${this._error}</div>`:t.length?null:_`<div class="empty">${this._t(e)}</div>`}};m(E,"properties",{open:{type:Boolean},_loading:{state:!0},_error:{state:!0}}),m(E,"styles",[D,Be]);var G=class extends E{constructor(){super(),this._routes=[]}updated(t){t.has("open")&&this.open&&this._load()}async _load(){if(!(!this.hass||!this.stop)){this._loading=!0,this._error=null;try{this._routes=await this.hass.callWS({type:`${v}/stop_routes`,stop_code:this.stop.code})}catch(t){this._error=q(this.hass,t)}finally{this._loading=!1}}}render(){let t=this.stop||{},e=this._renderState(this._routes,"noLines");return _`
      <${this._dialog}
        header-title=${t.name||this._t("stopDetails")}
        header-subtitle=${[t.city,t.code].filter(Boolean).join(" \xB7 ")}
        width="medium"
        .open=${this.open}
        @closed=${this._closed}
      >
        ${e??_`<div class="list">
            ${this._routes.map(i=>_`
                <div class="item">
                  <div
                    class="badge"
                    style=${`--it-badge-color:${T(i.route_type)}`}
                  >
                    ${i.line_name}
                  </div>
                  <div class="item-body">
                    <div class="item-title">${i.destination}</div>
                    <div class="item-sub">
                      ${[i.operator,bt(this.hass,i.route_type)].filter(Boolean).join(" \xB7 ")}
                    </div>
                  </div>
                  ${i.has_realtime?l:_`<span class="tag timetable"
                          >${this._t("scheduled")}</span
                        >`}
                </div>
              `)}
          </div>`}
      </${this._dialog}>
    `}};m(G,"properties",{...E.properties,stop:{attribute:!1},_routes:{state:!0}});var F=class extends E{constructor(){super(),this._stops=[],this.showMap=!0,this._mapReady=!1,this._paths=[],this._focus=[]}willUpdate(t){(t.has("arrival")||t.has("_stops")||t.has("stopCode"))&&(this._focus=this._computeFocus(),this._paths=this._computePaths())}updated(t){t.has("open")&&this.open&&this._load(),this._fitMap()}async _load(){if(this._stops=[],this._error=null,!this.hass||!this.arrival?.line_ref){this._error=this._t("noRouteStops");return}this._loading=!0,this.showMap&&Xt().then(t=>{this._mapReady=t});try{this._stops=await this.hass.callWS({type:`${v}/route_stops`,line_ref:this.arrival.line_ref,departed:this.arrival.departed||null})}catch(t){this._error=q(this.hass,t)}finally{this._loading=!1}}get _located(){return this._stops.filter(it)}get _vehiclePoint(){let{vehicle_lat:t,vehicle_lon:e}=this.arrival||{};return t!=null&&e!=null?[t,e]:null}get _hereIndex(){let{vehicle_lat:t,vehicle_lon:e}=this.arrival||{};return ze(this._stops,t,e)}get _mineIndex(){if(this.stopCode==null)return-1;let t=Number(this.stopCode);return this._stops.findIndex(e=>Number(e.code)===t)}_computeFocus(){let t=this._vehiclePoint,e=this._located.map(et);if(!t)return e;let i=this._hereIndex;if(i<0)return[t,...e];let s=this._mineIndex,r=s>i?Math.min(s,i+Te):i+Le,n=this._stops.slice(i,r+1).filter(it).map(et);return[t,...n.length?n:e]}_computePaths(){if(!this.showMap)return[];let t=this.arrival||{},e=new Date,i=je(this._focus),s=[],r=this._located.map(a=>({point:et(a),timestamp:Ie(a.arrival_time,e)}));r.length>1&&s.push({points:r,color:qt(t.route_type),name:`${t.line_name??""} ${this._t("routeLine")}`.trim()});let n=this._stops[this._mineIndex];n&&it(n)&&s.push(ie(et(n),i,yt,this._t("myStop"),e));let h=this._vehiclePoint;return h&&s.push(ie(h,i,Q,this._t("vehicleMap"),e)),s}_fitMap(){let t=this._focus.length?JSON.stringify(this._focus):"";if(!t||t===this._fitted)return;let e=this.renderRoot.querySelector("ha-map");if(e){if(!e.leafletMap){!this._fitTimer&&(this._fitTries??0)<Re&&(this._fitTries=(this._fitTries??0)+1,this._fitTimer=setTimeout(()=>{this._fitTimer=void 0,this._fitMap()},Ne));return}this._fitTries=0,e.fitBounds(this._focus,{zoom:te}),this._fitted=t}}disconnectedCallback(){super.disconnectedCallback(),clearTimeout(this._fitTimer),this._fitTimer=void 0}_renderMap(){return!this.showMap||!this._mapReady||!this._paths.length?l:_`
      <ha-map .hass=${this.hass} .paths=${this._paths} .zoom=${te}></ha-map>
      <div class="legend">
        ${this._paths.map(t=>_`<span class="key"
            ><i style=${`background:${t.color}`}></i>${t.name}</span
          >`)}
      </div>
    `}_relative(t){if(t==null)return"";let e=Math.round(t/60);return e?`+${e} ${this._t("minutes")}`:""}render(){let t=this.arrival||{},e=this._hereIndex,i=this._mineIndex,s=this._renderState(this._stops,"noRouteStops"),r=[bt(this.hass,t.route_type),t.line_name].filter(Boolean).join(" ");return _`
      <${this._dialog}
        header-title=${`${r} \xB7 ${t.destination||""}`}
        header-subtitle=${[t.operator,this._t("routeStops")].filter(Boolean).join(" \xB7 ")}
        width="medium"
        .open=${this.open}
        @closed=${this._closed}
      >
        ${this._renderMap()}
        ${e>=0||t.departed?_`<div class="note">
                <ha-icon .icon=${tt(t.route_type)}></ha-icon>
                <span>
                  ${e>=0?`${this._t("vehicleHere")}: ${this._stops[e].name}`:""}
                  ${t.departed?`${e>=0?" \xB7 ":""}${this._t("departedAt")}${V(t.departed,this.hass)}`:""}
                </span>
              </div>`:this.showMap&&t.is_realtime&&!this._vehiclePoint?_`<div class="note">
                  <ha-icon icon="mdi:map-marker-off-outline"></ha-icon>
                  <span>${this._t("noVehicleLocation")}</span>
                </div>`:l}
        ${s??_`<div class="list">
            ${this._stops.map((n,h)=>_`
                <div
                  class="stop ${h===e?"here":""} ${h===i?"mine":""}"
                >
                  <div class="track"><div class="node"></div></div>
                  <div>
                    <div class="stop-title">${n.name}</div>
                    <div class="stop-sub">
                      ${[n.city,n.code,h===i?this._t("myStop"):null].filter(Boolean).join(" \xB7 ")}
                    </div>
                  </div>
                  <div class="time">
                    ${n.arrival_time?V(n.arrival_time,this.hass):this._relative(n.offset_seconds)}
                  </div>
                </div>
              `)}
          </div>`}
      </${this._dialog}>
    `}};m(F,"properties",{...E.properties,arrival:{attribute:!1},showMap:{attribute:!1},stopCode:{attribute:!1},_stops:{state:!0},_mapReady:{state:!0}});var st=(o,t)=>{customElements.get(o)||customElements.define(o,t)};st("israel-transit-card",O);st("israel-transit-card-editor",P);st("israel-transit-stop-dialog",G);st("israel-transit-route-dialog",F);var oe={locale:{language:navigator.language||"he"}};window.customCards=window.customCards||[];window.customCards.some(o=>o.type==="israel-transit-card")||window.customCards.push({type:"israel-transit-card",name:f(oe,"name"),description:f(oe,"description"),preview:!0,documentationURL:"https://github.com/yosef-chai/israel-transit"});console.info("%c ISRAEL-TRANSIT-CARD %c v1.5.0 ","background:#2f7d4f;color:#fff;border-radius:3px 0 0 3px;padding:2px 4px","background:#1e6fbf;color:#fff;border-radius:0 3px 3px 0;padding:2px 4px");
