<template>
  <div class="download-page">
    <div class="download-card">
      <h1 class="title">Download</h1>
      <p class="helper">Paste an NCBI / Huawei Cloud / NovoCloud link; the system will auto-detect the source.</p>
      <div class="row">
        <textarea v-model.trim="url" placeholder="Paste the download link here" class="input textarea"></textarea>
        <div class="actions">
          <button :disabled="!url || loading" @click="start" class="btn">Start</button>
          <div v-if="progressVisible" class="progress-wrap">
            <div class="progress" :class="{ 'indeterminate': isIndeterminate }">
              <div class="progress-bar" :style="barStyle"></div>
            </div>
            <span class="progress-text">{{ progress }}%</span>
            <span v-if="humanSpeed" class="metric speed">{{ humanSpeed }}</span>
            <span v-if="humanETA" class="metric eta">预计完成：{{ humanETA }}</span>
            <button class="btn cancel" @click="cancel" :disabled="loading">Cancel</button>
          </div>
        </div>
      </div>
      <p v-if="provider" class="provider">Detected: {{ provider }}</p>
      <p v-if="msg" :class="['status', err ? 'error' : 'success']">{{ msg }}</p>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
export default {
  name: 'Download',
  data(){return{url:'',msg:'',err:false,loading:false,logPath:'',progressVisible:false,progress:0,poller:null,pollIntervalMs:1000,speedBps:0,etaSeconds:null,pid:null}},
  mounted(){
    const main = document.querySelector('main.container')
    if(main){
      main.classList.add('download-full-bleed')
    }
    // 如果有未完成的下载，自动恢复监控
    try{
      const saved = JSON.parse(localStorage.getItem('downloadSession')||'null')
      if(saved && saved.log){
        this.logPath = saved.log
        this.pid = saved.pid || null
        this.progressVisible = true
        this.beginPolling()
      }
    }catch(e){/* ignore */}
  },
  beforeUnmount(){
    const main = document.querySelector('main.container')
    if(main){
      main.classList.remove('download-full-bleed')
    }
    if(this.poller) clearInterval(this.poller)
  },
  computed:{
    provider(){const u=this.url||'';if(!u)return'';
      if(/ncbi\.nlm\.nih\.gov|ftp\.ncbi\.nlm\.nih\.gov/i.test(u)) return 'NCBI';
      if(/huaweicloud\.com|obs\.|cloud\.huawei/i.test(u)) return 'Huawei Cloud';
      if(/novogene\.com|novocloud|novo\.?cloud/i.test(u)) return 'NovoCloud';
      return 'Unknown';}
  },
  methods:{
    async start(){
      this.msg='';this.err=false;this.loading=true;this.progressVisible=false;this.progress=0;this.logPath='';
      try{
        const {data}=await axios.post('/api/downloads/start/',{url:this.url});
        this.msg=data?.message||'Submitted.';
        if(data?.log){
          this.logPath=data.log;
          this.pid = data?.pid || null;
          this.progressVisible=true;
          this.beginPolling();
          // Persist session for page navigation
          try{localStorage.setItem('downloadSession', JSON.stringify({log:this.logPath,pid:this.pid}))}catch(e){}
        }
      }catch(e){
        this.err=true;this.msg=e?.response?.data?.message||'Failed.';
        this.progressVisible=false;
      }finally{this.loading=false}
    },
    async cancel(){
      if(!this.logPath && !this.pid) return;
      try{
        await axios.post('/api/downloads/cancel/',{log:this.logPath,pid:this.pid});
        this.msg='Download canceled.';
      }catch(e){
        this.msg='Cancel failed';
      }
      this.stopPolling();
      try{localStorage.removeItem('downloadSession')}catch(e){}
    },
    beginPolling(){
      if(this.poller) clearInterval(this.poller);
      // 更快的刷新频率：默认每秒刷新一次速度与剩余时间
      this.poller=setInterval(this.pollOnce,this.pollIntervalMs);
      this.pollOnce();
    },
    async pollOnce(){
      if(!this.logPath) return;
      try{
        const {data}=await axios.get('/api/downloads/status/',{params:{log:this.logPath,n:50}});
        const p = typeof data?.percent==='number'?data.percent:0;
        this.progress=Math.max(0,Math.min(100,p));
        this.speedBps = data?.speed_bps || 0;
        this.etaSeconds = (data?.eta_seconds ?? null);
        if(this.progress>=100){
          this.stopPolling();
          this.msg='Completed.';
        }
      }catch(e){
        if(e?.response?.status===404){this.stopPolling()}
      }
    },
    stopPolling(){
      if(this.poller){clearInterval(this.poller);this.poller=null}
      this.progressVisible=false;
      try{localStorage.removeItem('downloadSession')}catch(e){}
    },
  },
  computed:{
    isIndeterminate(){
      // 只要百分比为 0，就显示不确定动画（即使暂时没有速度），避免静默状态
      return this.progress === 0;
    },
    barStyle(){
      if(this.isIndeterminate){
        // 在不确定模式下给定一个可见宽度，配合动画移动
        return { width: '30%' };
      }
      return { width: this.progress + '%' };
    },
    humanSpeed(){
      const s=this.speedBps||0; if(!s) return '';
      if(s<1024) return `${s} B/s`;
      if(s<1024*1024) return `${(s/1024).toFixed(1)} KB/s`;
      if(s<1024*1024*1024) return `${(s/1024/1024).toFixed(2)} MB/s`;
      return `${(s/1024/1024/1024).toFixed(2)} GB/s`;
    },
    humanETA(){
      const t=this.etaSeconds; if(t==null) return '';
      const h=Math.floor(t/3600);
      const m=Math.floor((t%3600)/60);
      const s=Math.floor(t%60);
      const parts=[]; if(h) parts.push(`${h}小时`); if(m) parts.push(`${m}分`); parts.push(`${s}秒`);
      return parts.join(' ');
    }
  }
}
</script>
<style scoped>
.download-page{width:100%;min-height:calc(100vh - 72px);padding:8px 12px;background:#fff;--primary: rgb(58, 126, 185);--primary-hover: rgb(45, 102, 150);display:flex;justify-content:center;align-items:flex-start;box-sizing:border-box}
.title{margin:0 0 12px 0;color:var(--waves-text-corporate, #1f2937);font-size:22px;font-weight:650;padding:0}

/* 卡片容器，使输入区域更大并更醒目 */
 .download-card{
  background: #fff;
  border-radius: var(--radius-sm);
  border: none;
  box-shadow: none;
  padding: 0px 0px; /* 恢复左右内边距，文字不贴边 */
  min-height: 760px;
  width: 100%;
  max-width: 3260px; /* 框更小，参考 Files 页体量 */
  display:flex;
  flex-direction:column;
 }

.helper{color:var(--waves-text-light, #6b7280);margin:0 0 16px 0;font-size:13px}
.row{display:flex;gap:12px;flex-direction:column;flex:1}
.input{
  flex:1;
  width:100%;
  padding:12px 16px;
  border: var(--waves-border-subtle, 1px solid #cbd5e1);
  border-radius: var(--radius-sm);
  background: var(--waves-card-secondary-bg, #fff);
  font-size: 16px;
  color: var(--waves-text-primary, #111827);
 }
.textarea{min-height:300px;line-height:1.7;resize:vertical;font-size:18px;flex:1;width:100%}
.actions{display:flex;align-items:center;gap:12px;justify-content:flex-start;margin-top:12px}
.btn{
  height:56px;
  padding:0 20px;
  border-radius: var(--radius-sm);
  background: var(--primary, rgb(58, 126, 185));
  color:#fff;
  border:1px solid var(--primary, rgb(58, 126, 185));
  font-weight:600;
}
.btn:not(:disabled):hover{ background: var(--primary-hover, rgb(45, 102, 150)); border-color: var(--primary-hover, rgb(45, 102, 150)); }
.btn:disabled{opacity:.6;cursor:not-allowed}
.btn.cancel{ background: var(--waves-error-600, #b91c1c); border-color: var(--waves-error-600, #b91c1c); height:28px; padding:0 12px; font-size:12px }
.progress-wrap{display:flex;align-items:center;gap:8px}
.progress{width:200px;height:8px;background:#e5e7eb;border-radius:6px;overflow:hidden}
.progress-bar{height:100%;background:var(--primary, rgb(58, 126, 185));transition:width .2s linear}
.progress-text{font-size:12px;color:#6b7280}
.progress.indeterminate{position:relative}
.progress.indeterminate .progress-bar{position:relative;animation:indeterminateMove 1.2s ease-in-out infinite}
@keyframes indeterminateMove{0%{transform:translateX(-100%)}50%{transform:translateX(60%)}100%{transform:translateX(-100%)}}
.metric{font-size:12px;color:#374151}
.metric.speed{font-weight:600}
.metric.eta{margin-left:4px}
.provider{margin-top:12px;color:var(--waves-text-light, #6b7280)}
.status{margin-top:8px;font-size:.95rem}
.status.success{color:var(--waves-success-600, #15803d)}
.status.error{color:var(--waves-error-600, #b91c1c)}
.helper, .provider, .status{padding:0}

/* 覆盖 App.vue 的 main.container 居中约束，使本页全屏贴边 */
:global(main.container.download-full-bleed){
  max-width: none !important;
  width: 100% !important;
  margin: 0 !important;
  padding: 12px 20px !important; /* 更贴边的页面间距 */
  align-items: flex-start !important;
  justify-content: flex-start !important;
  min-height: calc(100vh - 72px) !important;
  background: #fff !important;
}
</style>