var C='mochi-english-v4';
var CORE=['./','index.html','manifest.webmanifest','icons/icon-192.png','icons/icon-512.png','icons/apple-touch-icon.png'];
self.addEventListener('install',function(e){
  e.waitUntil(caches.open(C).then(function(c){return c.addAll(CORE)}).then(function(){return self.skipWaiting()}));
});
self.addEventListener('activate',function(e){
  e.waitUntil(caches.keys().then(function(ks){return Promise.all(ks.filter(function(k){return k.indexOf('mochi-english')===0&&k!==C}).map(function(k){return caches.delete(k)}))}).then(function(){return self.clients.claim()}));
});
self.addEventListener('fetch',function(e){
  if(e.request.method!=='GET')return;
  e.respondWith(caches.match(e.request).then(function(hit){
    var net=fetch(e.request).then(function(r){
      if(r&&(r.ok||r.type==='opaque')){var cp=r.clone();caches.open(C).then(function(c){c.put(e.request,cp)})}
      return r;
    }).catch(function(){return hit});
    return hit||net;
  }));
});
