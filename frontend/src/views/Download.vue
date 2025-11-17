<template>
  <div class="download-page">
    <div class="download-card">
      <h1 class="title">Download</h1>
      <p class="helper">Paste an NCBI / Huawei Cloud / NovoCloud link; the system will auto-detect the source.</p>
      <div class="row">
        <textarea v-model.trim="url" placeholder="Paste the download link here" class="input textarea"></textarea>
        <div class="actions">
          <button :disabled="!url" @click="start" class="btn">Start</button>
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
  data(){return{url:'',msg:'',err:false}},
  mounted(){
    const main = document.querySelector('main.container')
    if(main){
      main.classList.add('download-full-bleed')
    }
  },
  beforeUnmount(){
    const main = document.querySelector('main.container')
    if(main){
      main.classList.remove('download-full-bleed')
    }
  },
  computed:{
    provider(){const u=this.url||'';if(!u)return'';
      if(/ncbi\.nlm\.nih\.gov|ftp\.ncbi\.nlm\.nih\.gov/i.test(u)) return 'NCBI';
      if(/huaweicloud\.com|obs\.|cloud\.huawei/i.test(u)) return 'Huawei Cloud';
      if(/novogene\.com|novocloud|novo\.?cloud/i.test(u)) return 'NovoCloud';
      return 'Unknown';}
  },
  methods:{
    async start(){this.msg='';this.err=false;try{
      const {data}=await axios.post('/api/downloads/start/',{url:this.url});
      this.msg=data?.message||'Submitted.';
    }catch(e){this.err=true;this.msg=e?.response?.data?.message||'Failed.';}}
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