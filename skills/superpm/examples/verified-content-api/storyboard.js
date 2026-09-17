/* 검증 교육 콘텐츠 API · 화면설계서 컨트롤 (외부 의존 0) — 모든 sb 페이지에서 링크.
   글자 크기 · 콜아웃 번호 진하기 · 화면 확대/축소 · 원본 보기 라이트박스 · 목차 스크롤 */
(function(){
  /* ── 글자 크기 + 콜아웃 번호 진하기 (localStorage, 탭 간 동기화) ── */
  var r=document.documentElement,FZ='sbFz',OP='sbCueOp',S=[1,1.12,1.26,1.42];
  function cl(i){i=parseInt(i,10)||0;return Math.max(0,Math.min(S.length-1,i));}
  function gF(){try{return cl(localStorage.getItem(FZ))}catch(e){return 0}}
  function gO(){try{var v=parseInt(localStorage.getItem(OP),10);return(v>=20&&v<=100)?v:100}catch(e){return 100}}
  function aF(i){r.style.setProperty('--sb-fz',S[cl(i)]);}
  function aO(v){r.style.setProperty('--sb-cue-op',(v/100).toFixed(2));}
  aF(gF());aO(gO());
  function wireSettings(){var fi=gF();
    document.querySelectorAll('[data-fz]').forEach(function(b){b.addEventListener('click',function(){
      var a=b.dataset.fz;fi=a==='inc'?cl(fi+1):a==='dec'?cl(fi-1):0;aF(fi);try{localStorage.setItem(FZ,fi)}catch(e){}});});
    var s=document.querySelector('[data-op]');
    if(s){s.value=gO();s.addEventListener('input',function(){aO(s.value);try{localStorage.setItem(OP,s.value)}catch(e){}});}}
  window.addEventListener('storage',function(e){if(e.key===FZ)aF(gF());
    if(e.key===OP){aO(gO());var s=document.querySelector('[data-op]');if(s)s.value=gO();}});

  /* ── 화면 확대/축소: 휠(커서 기준) · ＋－·맞춤 · 드래그 · 더블클릭 ── */
  function initZoom(box){var stage=box.querySelector('.sb-stage');if(!stage)return;
    var pane=box.closest('.sb-pane')||box.parentNode,z=1,tx=0,ty=0,MIN=1,MAX=6,drag=false,sx=0,sy=0,btx=0,bty=0,
        lbl=pane.querySelector('.zlvl');
    function clamp(){var rc=box.getBoundingClientRect(),w=stage.offsetWidth*z,h=stage.offsetHeight*z;
      tx=Math.max(Math.min(0,rc.width-w),Math.min(0,tx));ty=Math.max(Math.min(0,rc.height-h),Math.min(0,ty));}
    function apply(){clamp();stage.style.transform='translate('+tx+'px,'+ty+'px) scale('+z+')';
      box.classList.toggle('zoomed',z>1);if(lbl)lbl.textContent=Math.round(z*100)+'%';}
    function zoomAt(cx,cy,nz){nz=Math.max(MIN,Math.min(MAX,nz));var rc=box.getBoundingClientRect(),
      ox=cx-rc.left,oy=cy-rc.top;tx=ox-(ox-tx)*(nz/z);ty=oy-(oy-ty)*(nz/z);z=nz;apply();}
    function reset(){z=1;tx=0;ty=0;apply();}
    box.addEventListener('wheel',function(e){e.preventDefault();zoomAt(e.clientX,e.clientY,z*(e.deltaY<0?1.15:1/1.15));},{passive:false});
    box.addEventListener('pointerdown',function(e){if(z<=1)return;drag=true;box.classList.add('dragging');
      sx=e.clientX;sy=e.clientY;btx=tx;bty=ty;try{box.setPointerCapture(e.pointerId)}catch(_){}});
    box.addEventListener('pointermove',function(e){if(!drag)return;tx=btx+(e.clientX-sx);ty=bty+(e.clientY-sy);apply();});
    function end(){drag=false;box.classList.remove('dragging');}
    box.addEventListener('pointerup',end);box.addEventListener('pointercancel',end);
    box.addEventListener('dblclick',function(e){e.preventDefault();reset();});
    pane.querySelectorAll('.sb-zoomctl [data-z]').forEach(function(b){b.addEventListener('click',function(){
      var rc=box.getBoundingClientRect(),cx=rc.left+rc.width/2,cy=rc.top+rc.height/2,a=b.dataset.z;
      if(a==='in')zoomAt(cx,cy,z*1.3);else if(a==='out')zoomAt(cx,cy,z/1.3);else reset();});});
    apply();}

  /* ── 원본 보기: .sb-stage 복제 → 전체화면 뷰어 ── */
  function initLightbox(){var lb=document.getElementById('sbLb');if(!lb)return;
    var zoom=document.getElementById('sbLbZoom'),stage=document.getElementById('sbLbStage'),
        title=document.getElementById('sbLbTitle'),lvl=lb.querySelector('.zlvl');
    var z=1,fit=1,tx=0,ty=0,drag=false,sx=0,sy=0,btx=0,bty=0;
    function apply(){stage.style.transform='translate('+tx+'px,'+ty+'px) scale('+z+')';if(lvl)lvl.textContent=Math.round(z/fit*100)+'%';}
    function fitNow(){var rc=zoom.getBoundingClientRect(),w=stage.offsetWidth||1,h=stage.offsetHeight||1;
      fit=Math.min(rc.width/w,rc.height/h)||1;z=fit;tx=(rc.width-w*z)/2;ty=(rc.height-h*z)/2;apply();}
    function open(sel,t){var src=document.querySelector(sel||'.sb-screen .sb-stage');
      stage.innerHTML=src?src.innerHTML:'';title.textContent=t||'원본 보기';lb.hidden=false;requestAnimationFrame(fitNow);}
    function close(){lb.hidden=true;stage.innerHTML='';}
    function zoomAt(cx,cy,nz){var mn=fit*0.5,mx=Math.max(1,fit)*8;nz=Math.max(mn,Math.min(mx,nz));
      var rc=zoom.getBoundingClientRect(),ox=cx-rc.left,oy=cy-rc.top;tx=ox-(ox-tx)*(nz/z);ty=oy-(oy-ty)*(nz/z);z=nz;apply();}
    document.querySelectorAll('[data-lb-stage]').forEach(function(b){b.addEventListener('click',function(e){
      e.preventDefault();open(b.getAttribute('data-lb-stage'),b.getAttribute('data-title'));});});
    lb.querySelectorAll('[data-lbclose]').forEach(function(b){b.addEventListener('click',close);});
    lb.addEventListener('click',function(e){if(e.target===lb)close();});
    document.addEventListener('keydown',function(e){if(!lb.hidden&&e.key==='Escape')close();});
    zoom.addEventListener('wheel',function(e){e.preventDefault();zoomAt(e.clientX,e.clientY,z*(e.deltaY<0?1.15:1/1.15));},{passive:false});
    zoom.addEventListener('pointerdown',function(e){drag=true;zoom.classList.add('dragging');
      sx=e.clientX;sy=e.clientY;btx=tx;bty=ty;try{zoom.setPointerCapture(e.pointerId)}catch(_){}});
    zoom.addEventListener('pointermove',function(e){if(!drag)return;tx=btx+(e.clientX-sx);ty=bty+(e.clientY-sy);apply();});
    function end(){drag=false;zoom.classList.remove('dragging');}
    zoom.addEventListener('pointerup',end);zoom.addEventListener('pointercancel',end);
    lb.querySelectorAll('.sb-zoomctl [data-z]').forEach(function(b){b.addEventListener('click',function(){
      var rc=zoom.getBoundingClientRect(),cx=rc.left+rc.width/2,cy=rc.top+rc.height/2,a=b.dataset.z;
      if(a==='in')zoomAt(cx,cy,z*1.3);else if(a==='out')zoomAt(cx,cy,z/1.3);else fitNow();});});
    window.addEventListener('resize',function(){if(!lb.hidden)fitNow();});}

  /* ── 목차에서 현재 화면 스크롤 ── */
  function tocScroll(){var c=document.querySelector('.sb-toc a.t.current'),t=document.querySelector('.sb-toc');
    if(c&&t)t.scrollTop=c.offsetTop-t.clientHeight/2+20;}

  function boot(){wireSettings();document.querySelectorAll('.sb-screen .sb-zoom').forEach(initZoom);initLightbox();tocScroll();}
  if(document.readyState!=='loading')boot();else document.addEventListener('DOMContentLoaded',boot);
})();
