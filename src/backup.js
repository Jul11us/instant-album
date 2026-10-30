/* Portable editable album backups. Parsing only returns data; it never writes storage. */
(() => {
  'use strict';
  const MARKER = 'instant-album-backup', VERSION = 1, MIB = 1024 * 1024;
  const LIMITS = Object.freeze({bytes:300*MIB, fileBytes:420*MIB, blobBytes:100*MIB,
    entries:3001, photos:500, albums:1000, pages:1000, side:8192, pixels:32*1024*1024,
    totalPixels:200*1024*1024});
  const FORMATS = {
    mini:['mini','instax mini · 竖长',54,86,[4,7,46,62]],
    square:['square','instax SQUARE · 方形',72,86,[5,7,62,62]],
    wide:['wide','instax WIDE · 横宽',108,86,[4.5,7,99,62]],
    polaroid:['Polaroid','宝丽来 i-Type/600 · 方形',88,107,[4.5,6,79,77]],
    go:['Go','宝丽来 Go · 小方形',53.9,66.6,[3.45,4.5,47,46]],
    free:['原比例','原比例 · 不按相纸']
  };
  const FILTERS = ['原片','旧夏','海盐','柯达金','雾','褪色','夜蓝','墨'];
  const FRAMES = ['orig','none','draw','upload','black','pinklemon','rainbow','macaron',
    'mermaid','confetti','contact','hearts','galaxy','glitter','lavender','spray','sprinkles',
    'slide','starlight','metal','pblack','pyellow','pred','porange','pblue','pgreen',
    'pround','pgold','pgrad','#FFFFFF','#F7D84A','#FF8FB1','#10153A'];
  const FONTS = ['longcang','mashan','zhimang','caocao','kuaile','huangyou','xiaowei',
    'round','song','hei','caveat','typewriter'];
  const KEY = /^(?:meta|frame:(?:draw|upload)|(?:src|orig|film|back):[a-zA-Z0-9_-]{1,80})$/;
  const ID = /^[a-zA-Z0-9_-]{1,80}$/;
  const fail = message => {throw new Error('备份无法读取：'+message)};
  const object = (v,keys,label) => {
    if(!v||typeof v!=='object'||Array.isArray(v)||
      ![Object.prototype,null].includes(Object.getPrototypeOf(v)))fail(label+'格式不正确');
    if(Object.keys(v).some(k=>!keys.includes(k)))fail(label+'含不支持的字段');
    return v;
  };
  const text = (v,max,label) => {if(typeof v!=='string'||v.length>max)fail(label+'格式不正确');return v};
  const id = (v,label) => {if(typeof v!=='string'||!ID.test(v)||Object.hasOwn(Object.prototype,v)||['prototype','all','new'].includes(v))fail(label+'无效');return v};
  const number = (v,min,max,label,integer=false) => {
    if(typeof v!=='number'||!Number.isFinite(v)||v<min||v>max||integer&&!Number.isInteger(v))fail(label+'超出范围');return v;
  };
  const bool = (v,label) => {if(typeof v!=='boolean')fail(label+'格式不正确')};
  const choice = (v,values,label) => {if(!values.includes(v))fail(label+'不受支持');return v};
  const array = (v,max,label) => {if(!Array.isArray(v)||v.length>max)fail(label+'格式不正确');return v};
  const date = (v,label) => {
    text(v,10,label);if(v==='')return;
    if(!/^\d{4}-\d{2}-\d{2}$/.test(v))fail(label+'无效');
    const [y,m,d]=v.split('-').map(Number),days=new Date(Date.UTC(y===0?400:y,m,0)).getUTCDate();
    if(y<1||m<1||m>12||d<1||d>days)fail(label+'无效');
  };
  const unique = (values,label) => {if(new Set(values).size!==values.length)fail(label+'重复')};
  function validateState(st){
    object(st,['filter','bright','contrast','warm','grain','frame','caption','font','capOff',
      'sticker','sx','sy','date','memo','spots','hand'],'编辑参数');
    choice(st.filter,FILTERS,'滤镜');choice(st.frame,FRAMES,'边框');
    for(const k of ['bright','contrast','warm'])number(st[k],-50,50,k);
    number(st.grain,0,50,'颗粒');text(st.caption,10000,'文字');
    if(st.font!==undefined)choice(st.font,FONTS,'字体');
    if(st.hand!==undefined)bool(st.hand,'旧版字体');
    bool(st.capOff,'文字开关');number(st.sticker,0,3,'贴纸',true);
    number(st.sx,0,1,'贴纸位置');number(st.sy,0,1,'贴纸位置');
    const dt=object(st.date,['on','d','fmt','look','pos','guess','p','s','adjusted'],'照片日期');
    bool(dt.on,'日期开关');date(dt.d,'照片日期');choice(dt.fmt,['YY.MM.DD','DD.MM.YY','MM/DD/YY'],'日期格式');
    choice(dt.look,['led','white','ink'],'日期样式');choice(dt.pos,['photo','frame'],'日期位置');bool(dt.guess,'日期来源');
    if(dt.p!==undefined)choice(dt.p,['day','month','season','year','about','none'],'日期精度');
    if(dt.s!==undefined)choice(dt.s,['spring','summer','autumn','winter'],'季节');
    if(dt.adjusted!==undefined)bool(dt.adjusted,'日期调整');
    const memo=object(st.memo,['place','people','story','print'],'回忆');
    text(memo.place,1000,'地点');text(memo.people,1000,'人物');text(memo.story,20000,'故事');
    array(memo.print,2,'白边文字').forEach(k=>choice(k,['place','people'],'白边文字'));unique(memo.print,'白边文字');
    if(st.spots!==undefined)array(st.spots,20000,'光斑修补').forEach(p=>{
      if(!Array.isArray(p)||p.length!==3)fail('光斑修补格式不正确');
      number(p[0],0,1,'光斑位置');number(p[1],0,1,'光斑位置');number(p[2],.001,.5,'画笔大小');
    });
  }
  function validateFormat(F,fmt){
    object(F,['name','label','W','H','img','free'],'相纸');
    const spec=FORMATS[fmt];if(F.name!==spec[0]||F.label!==spec[1])fail('相纸名称无效');
    number(F.W,.01,1000,'相纸宽度');number(F.H,.01,1000,'相纸高度');
    if(!Array.isArray(F.img)||F.img.length!==4)fail('相纸画面无效');
    F.img.forEach((n,i)=>number(n,i<2?0:.01,1000,'相纸画面'));
    if(F.img[0]+F.img[2]>F.W+.001||F.img[1]+F.img[3]>F.H+.001)fail('相纸画面超出边界');
    if(F.free!==undefined)bool(F.free,'相纸比例开关');
    if(fmt==='free'){if(F.free!==true)fail('原比例相纸无效')}
    else if(F.free===true||Math.abs(F.W-spec[2])>.001||Math.abs(F.H-spec[3])>.001||F.img.some((n,i)=>Math.abs(n-spec[4][i])>.001))fail('相纸规格无效');
  }
  function validateQuad(q){
    if(!Array.isArray(q)||q.length!==4)fail('照片四角无效');
    q.forEach(p=>{if(!Array.isArray(p)||p.length!==2)fail('照片四角无效');p.forEach(n=>number(n,0,LIMITS.side,'照片四角'))});
    const turns=q.map((p,i)=>{const b=q[(i+1)%4],c=q[(i+2)%4];return (b[0]-p[0])*(c[1]-b[1])-(b[1]-p[1])*(c[0]-b[0])});
    if(!turns.every(v=>v>.1)&&!turns.every(v=>v<-.1))fail('照片四角交叉或重合');
    const area=Math.abs(q.reduce((s,p,i)=>{const n=q[(i+1)%4];return s+p[0]*n[1]-n[0]*p[1]},0))/2;
    if(area<64)fail('照片选框过小');
  }
  function validateMeta(meta,map){
    object(meta,['v','cur','list','cols','pages'],'相册数据');if(meta.v!==1)fail('相册数据版本不受支持');
    array(meta.list,LIMITS.photos,'照片');number(meta.cur,0,Math.max(0,meta.list.length-1),'当前照片',true);
    const ids=new Set(),rows=meta.list;
    for(const r of rows){
      object(r,['id','srcId','ow','fmt','F','quad','st','merged','scanDate','scanSrc','back'],'照片数据');
      id(r.id,'照片标识');id(r.srcId,'原图标识');if(ids.has(r.id))fail('照片标识重复');ids.add(r.id);
      if(r.ow!==undefined)number(r.ow,1,100000,'原图宽度',true);
      choice(r.fmt,Object.keys(FORMATS),'相纸型号');validateFormat(r.F,r.fmt);validateQuad(r.quad);validateState(r.st);
      bool(r.merged,'合成状态');bool(r.back,'背面状态');date(r.scanDate,'翻拍日期');choice(r.scanSrc,['exif','file','today'],'翻拍日期来源');
      for(const k of ['src:'+r.srcId,'film:'+r.id,...(r.back?['back:'+r.id]:[])])if(!map.has(k))fail('缺少照片文件 '+k);
      if(['draw','upload'].includes(r.st.frame)&&!map.has('frame:'+r.st.frame))fail('缺少自定义边框');
    }
    const cols=meta.cols===undefined?[]:array(meta.cols,LIMITS.albums,'相册');
    unique(cols.map(c=>id(c.id,'相册标识')),'相册标识');
    for(const c of cols){object(c,['id','name','cover','ids'],'相册');text(c.name,200,'相册名称');
      if(c.cover!==null&&c.cover!==undefined)id(c.cover,'相册封面');
      array(c.ids,LIMITS.photos,'相册照片').forEach(k=>{id(k,'相册照片');if(!ids.has(k))fail('相册引用了不存在的照片')});unique(c.ids,'相册照片')}
    const pages=meta.pages===undefined?[]:array(meta.pages,LIMITS.pages,'相册页');
    unique(pages.map(p=>id(p.id,'相册页标识')),'相册页标识');
    for(const p of pages){object(p,['id','tpl','pick','title','bg','tape','tilt','seed','t'],'相册页');
      choice(p.tpl,['wall','contact','postcard','timeline'],'拼页样式');text(p.title,200,'相册页标题');
      if(p.bg!==null&&(typeof p.bg!=='string'||!/^#[0-9a-f]{6}$/i.test(p.bg)))fail('相册页底色无效');
      choice(p.tape,['color','kraft','clear','none'],'胶带');number(p.tilt,0,2,'照片摆放');number(p.seed,0,Number.MAX_SAFE_INTEGER,'摆放序号',true);number(p.t,0,8640000000000000,'保存时间');
      array(p.pick,({wall:9,contact:12,postcard:2,timeline:8})[p.tpl],'相册页照片').forEach(k=>{id(k,'相册页照片');if(!ids.has(k))fail('相册页引用了不存在的照片')});unique(p.pick,'相册页照片');
    }
    return rows;
  }
  async function rasterDimensions(blob){
    const a=new Uint8Array(await blob.slice(0,262144).arrayBuffer());let w,h;
    if(a.length>=24&&a[0]===137&&a[1]===80&&a[2]===78&&a[3]===71&&a[4]===13&&a[5]===10&&a[6]===26&&a[7]===10&&String.fromCharCode(...a.slice(12,16))==='IHDR'){
      const v=new DataView(a.buffer);w=v.getUint32(16);h=v.getUint32(20);
    }else if(a[0]===255&&a[1]===216){
      for(let i=2;i<a.length;){if(a[i++]!==255)fail('JPEG 文件损坏');while(a[i]===255)i++;const marker=a[i++];
        if(marker===218||marker===217)break;if(marker===1||marker>=208&&marker<=215)continue;
        if(i+2>a.length)break;const n=a[i]*256+a[i+1];if(n<2)fail('JPEG 文件损坏');
        if([192,193,194,195,197,198,199,201,202,203,205,206,207].includes(marker)){if(i+7>a.length)break;h=a[i+3]*256+a[i+4];w=a[i+5]*256+a[i+6];break}i+=n;
      }
    }
    number(w,2,LIMITS.side,'照片宽度',true);number(h,2,LIMITS.side,'照片高度',true);
    if(w*h>LIMITS.pixels)fail('照片像素过大');
    let im;try{im=await createImageBitmap(blob);if(im.width!==w||im.height!==h)fail('照片尺寸不一致')}
    catch(e){fail('照片文件损坏或无法解码')}finally{im?.close()}
    return {width:w,height:h};
  }
  async function validate(entries){
    array(entries,LIMITS.entries,'备份条目');const map=new Map(),dimensions=new Map();let bytes=0,pixels=0;
    for(const entry of entries){
      if(!Array.isArray(entry)||entry.length!==2||typeof entry[0]!=='string'||!KEY.test(entry[0]))fail('含不支持的存储条目');
      const [key,value]=entry;if(map.has(key))fail('存储条目重复');map.set(key,value);
      if(key==='meta'){if(value instanceof Blob)fail('相册数据格式不正确');continue}
      if(!(value instanceof Blob)||!value.size||value.size>LIMITS.blobBytes)fail('照片文件大小无效');
      if(!/^image\/[a-z0-9.+-]{1,60}$/i.test(value.type))fail('照片文件类型无效');
      bytes+=value.size;if(bytes>LIMITS.bytes)fail('备份照片总量超过 300 MB');
      if(!key.startsWith('orig:')){
        if(!['image/jpeg','image/png'].includes(value.type))fail('扫描文件类型不受支持');
        const d=await rasterDimensions(value);pixels+=d.width*d.height;if(pixels>LIMITS.totalPixels)fail('备份照片像素总量过大');dimensions.set(key,d);
      }
    }
    if(entries.length&&!map.has('meta'))fail('缺少相册数据');
    if(map.has('meta')){
      const rows=validateMeta(map.get('meta'),map);
      for(const r of rows){const d=dimensions.get('src:'+r.srcId);if(r.quad.some(p=>p[0]>d.width+.01||p[1]>d.height+.01))fail('照片四角超出原图');
        const film=dimensions.get('film:'+r.id);if(Math.abs(film.width/film.height-r.F.W/r.F.H)>.015*Math.max(1,r.F.W/r.F.H))fail('照片与相纸比例不一致');
        if(Math.round((r.F.img[2]/r.F.W-.024)*film.width)<2||Math.round((r.F.img[3]/r.F.H-.024)*film.height)<2)fail('相纸的可用画面过小')}
    }
    return entries;
  }
  const CRC=(()=>{const t=new Uint32Array(256);for(let i=0;i<256;i++){let c=i;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[i]=c>>>0}return t})();
  const checksum=a=>{let c=0xFFFFFFFF;for(const b of a)c=CRC[(c^b)&255]^(c>>>8);return ((c^0xFFFFFFFF)>>>0).toString(16).padStart(8,'0')};
  const encode=a=>{const parts=[];for(let i=0;i<a.length;i+=32768)parts.push(String.fromCharCode(...a.subarray(i,i+32768)));return btoa(parts.join(''))};
  async function create(entries){
    await validate(entries);const packed=[];
    for(const [key,value] of entries){if(key==='meta'){packed.push({key,kind:'json',value});continue}
      const bytes=new Uint8Array(await value.arrayBuffer());packed.push({key,kind:'blob',mime:value.type,size:value.size,checksum:checksum(bytes),data:encode(bytes)})}
    const file=new Blob([JSON.stringify({marker:MARKER,version:VERSION,createdAt:new Date().toISOString(),entries:packed})],{type:'application/json'});
    if(file.size>LIMITS.fileBytes)fail('备份文件超过大小限制，当前收藏未改变');
    return file;
  }
  async function parse(file){
    if(!(file instanceof Blob)||!file.size||file.size>LIMITS.fileBytes)fail('文件为空或过大');
    let archive;try{archive=JSON.parse(await file.text())}catch(e){fail('文件不是有效的 JSON 备份')}
    object(archive,['marker','version','createdAt','entries'],'备份');
    if(archive.marker!==MARKER||archive.version!==VERSION)fail('备份格式或版本不受支持');
    text(archive.createdAt,40,'备份时间');if(!Number.isFinite(Date.parse(archive.createdAt)))fail('备份时间无效');
    array(archive.entries,LIMITS.entries,'备份条目');const entries=[],keys=new Set();let total=0;
    for(const entry of archive.entries){
      object(entry,['key','kind','value','mime','size','checksum','data'],'备份条目');
      if(typeof entry.key!=='string'||!KEY.test(entry.key)||keys.has(entry.key))fail('备份存储条目无效或重复');keys.add(entry.key);
      if(entry.key==='meta'){
        if(entry.kind!=='json'||Object.keys(entry).some(k=>!['key','kind','value'].includes(k)))fail('相册条目无效');entries.push([entry.key,entry.value]);continue;
      }
      if(entry.kind!=='blob'||Object.hasOwn(entry,'value'))fail('照片条目无效');
      number(entry.size,1,LIMITS.blobBytes,'照片文件大小',true);total+=entry.size;if(total>LIMITS.bytes)fail('备份照片总量超过 300 MB');
      if(typeof entry.mime!=='string'||!/^image\/[a-z0-9.+-]{1,60}$/i.test(entry.mime))fail('照片文件类型无效');
      if(typeof entry.data!=='string'||entry.data.length!==Math.ceil(entry.size/3)*4||/[^A-Za-z0-9+/=]/.test(entry.data)||
        entry.data.includes('=')&&!/^[^=]*={1,2}$/.test(entry.data))fail('照片编码损坏');
      if(typeof entry.checksum!=='string'||! /^[0-9a-f]{8}$/.test(entry.checksum))fail('照片校验信息无效');
      let raw;try{raw=atob(entry.data)}catch(e){fail('照片编码损坏')}
      if(raw.length!==entry.size)fail('照片文件长度不一致');
      const data=new Uint8Array(raw.length);for(let i=0;i<raw.length;i++)data[i]=raw.charCodeAt(i);
      if(checksum(data)!==entry.checksum)fail('照片校验失败，文件可能已损坏');
      entries.push([entry.key,new Blob([data],{type:entry.mime})]);
    }
    await validate(entries);return entries;
  }
  globalThis.AlbumBackup=Object.freeze({create,parse,validate,limits:LIMITS,marker:MARKER,version:VERSION});
})();
