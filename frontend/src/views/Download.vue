<template>
  <div class="download-page">
    <div class="content-layout">
    <div class="download-card">
      <h1 class="title">Download</h1>
      <p class="helper">Paste an NCBI / Huawei Cloud / NovoCloud link; the system will auto-detect the source.</p>
      <div class="row">
        <textarea ref="urlInput" v-model.trim="url" placeholder="Paste the download link here" class="input textarea"></textarea>
        <div class="actions">
          <button :disabled="!url || loading" @click="openOutdirDialog" class="btn">Start</button>
          <div v-if="progressVisible" class="progress-wrap">
            <div class="progress" :class="{ 'indeterminate': isIndeterminate }">
              <div class="progress-bar" :style="barStyle"></div>
            </div>
            <span class="progress-text">{{ progress }}%</span>
            <span v-if="humanSpeed" class="metric speed">{{ humanSpeed }}</span>
            <span v-if="humanETA" class="metric eta">预计完成：{{ humanETA }}</span>
            <button class="btn cancel" @click="cancel" :disabled="loading">Cancel</button>
            <button v-if="debug" class="btn test" @click="progress = Math.min(100, progress + 10)">Test</button>
          </div>
        </div>
      </div>
      <p v-if="provider" class="provider">Detected: {{ provider }}</p>
      <p v-if="msg" :class="['status', err ? 'error' : 'success']">{{ msg }}</p>

      <!-- 目录选择弹窗 -->
      <div v-if="showOutdirDialog" class="dialog-backdrop">
        <div class="dialog">
          <h3 class="dialog-title">Select Download Folder</h3>
          <div class="dialog-body">
            <p class="helper">Choose a folder from the Files page; data will be saved to the corresponding relative path (under the downloads root).</p>
            <select v-model="selectedFolderPath" class="input outdir">
              <option v-for="f in folderOptions" :key="f.id" :value="f.folder_path">{{ f.folder_path }}</option>
            </select>
            <div class="create-row" v-if="showCreateInput">
              <label class="create-label">Create under current folder</label>
              <input v-model.trim="newFolderName" class="input" placeholder="Filename" />
              <button class="btn sm" :disabled="creating || !newFolderName" @click="createFolder">Create</button>
              <button class="btn sm secondary" :disabled="creating" @click="hideCreateInput">Cancel</button>
            </div>
            <div class="create-row" v-else>
              <button class="btn sm" @click="showCreateInput = true">New</button>
            </div>
            <p v-if="folderCreateError" class="status error">{{ folderCreateError }}</p>
          </div>
          <div class="dialog-actions">
            <button class="btn secondary" @click="cancelOutdir">Cancel</button>
            <button class="btn" @click="confirmOutdir">Confirm</button>
          </div>
        </div>
      </div>
    </div>
    <div class="jobs-panel">
      <div class="jobs-header">
        <div class="jobs-actions">
          <button class="btn sm" @click="focusUrlInput">下载任务</button>
          <button class="btn sm" @click="refreshJobs" :disabled="jobsLoading">刷新</button>
        </div>
        <div class="jobs-filter">
          <button class="filter-btn" :class="{active: statusFilter==='all'}" @click="statusFilter='all'">全部</button>
          <button class="filter-btn" :class="{active: statusFilter===1}" @click="statusFilter=1">进行中</button>
          <button class="filter-btn" :class="{active: statusFilter===3}" @click="statusFilter=3">失败</button>
          <button class="filter-btn" :class="{active: statusFilter===2}" @click="statusFilter=2">已完成</button>
        </div>
      </div>
      <div class="jobs-list">
        <div v-if="jobsLoading" class="jobs-empty">加载中...</div>
        <div v-else-if="jobs.length===0" class="jobs-empty">暂无任务</div>
        <div v-else class="jobs-items">
          <div v-for="j in filteredJobs" :key="j.id" class="job-item">
            <div class="job-card-top">
              <div class="job-main">
                <div class="job-name">{{ j.file_name || j.task_name }}</div>
                <div class="job-meta">{{ formatTime(j.created_at) }}</div>
                <div v-if="j.task_status===1 && jobProgress[j.id] != null" class="mini-progress">
                  <div class="mini-progress-bar" :style="{ width: (jobProgress[j.id] || 0) + '%' }"></div>
                </div>
              </div>
              <div class="job-right">
                <span :class="['badge', statusClass(j.task_status)]">{{ statusText(j.task_status) }}</span>
                <div class="job-actions">
                  <template v-if="j.task_status===1">
                    <button class="btn sm cancel" @click="cancelJob(j)">取消</button>
                    <button class="btn sm secondary" @click="toggleDetails(j)">详情</button>
                  </template>
                  <template v-else-if="j.task_status===3">
                    <button class="btn sm" @click="retryJob(j)">重试</button>
                    <button class="btn sm secondary" @click="toggleDetails(j)">详情</button>
                    <button class="btn sm cancel" @click="deleteJob(j)">删除</button>
                  </template>
                  <template v-else-if="j.task_status===2">
                    <button class="btn sm secondary" @click="toggleDetails(j)">详情</button>
                    <button class="btn sm cancel" @click="deleteJob(j)">删除</button>
                  </template>
                  <template v-else>
                    <button class="btn sm secondary" @click="toggleDetails(j)">详情</button>
                    <button class="btn sm cancel" @click="deleteJob(j)">删除</button>
                  </template>
                </div>
              </div>
            </div>
            <div v-if="expandedJobs[j.id]" class="job-details">
              <div class="job-details-body">
                <div v-if="loadingLogs[j.id]" class="jobs-empty">加载详情...</div>
                <pre v-else class="job-logs">{{ jobLogs[j.id] || '暂无详情' }}</pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>
<script>
import axios from 'axios'
export default {
  name: 'Download',
  data(){return{url:'',outdir:'downloads',msg:'',err:false,loading:false,logPath:'',progressVisible:false,progress:0,poller:null,pollIntervalMs:1000,speedBps:0,etaSeconds:null,pid:null,showOutdirDialog:false,tmpOutdir:'downloads',folderOptions:[],selectedFolderPath:'',newFolderName:'',creating:false,folderCreateError:'',showCreateInput:false,debug:false,jobs:[],jobsLoading:false,jobsPoller:null,statusFilter:'all',expandedJobs:{},jobLogs:{},loadingLogs:{},jobProgress:{}}},
  created(){
    try{
      const savedOut = localStorage.getItem('downloadOutdir')
      if(savedOut){ this.outdir = savedOut; this.tmpOutdir = savedOut; this.selectedFolderPath = savedOut }
      const dbgParam = new URLSearchParams(window.location.search).get('debug')
      const dbgLocal = localStorage.getItem('downloadDebug')
      this.debug = (dbgParam === '1') || (dbgLocal === '1')
    }catch(e){/* ignore */}
  },
  mounted(){
    const main = document.querySelector('main.container')
    if(main){
      main.classList.add('download-full-bleed')
    }
    try{
      const params = new URLSearchParams(window.location.search)
      const fileId = params.get('file')
      const folderId = params.get('folder')
      const accept = params.get('accept')
      if (fileId || folderId) {
        // 对站内分享链接默认进行“保存到我的文件”操作；若显式 accept=0 则走直接下载
        if (accept === '0') {
          if (fileId) { this.autoDownloadFileById(Number(fileId)) }
          else if (folderId) { this.autoDownloadFolderById(Number(folderId)) }
        } else {
          if (fileId) { this.acceptSharedFile(Number(fileId)) }
          else if (folderId) { this.acceptSharedFolder(Number(folderId)) }
        }
      }
    }catch(e){}
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
    this.refreshJobs()
    this.beginJobsPolling()
  },
  beforeUnmount(){
    const main = document.querySelector('main.container')
    if(main){
      main.classList.remove('download-full-bleed')
    }
    if(this.poller) clearInterval(this.poller)
    if(this.jobsPoller) clearInterval(this.jobsPoller)
  },
  watch:{
    url(newVal){
      if(newVal){ this.tryAutoDownloadFromLink(newVal) }
    }
  },
  computed:{
    provider(){const u=this.url||'';if(!u)return'';
      if(/ncbi\.nlm\.nih\.gov|ftp\.ncbi\.nlm\.nih\.gov/i.test(u)) return 'NCBI';
      if(/huaweicloud\.com|obs\.|cloud\.huawei/i.test(u)) return 'Huawei Cloud';
      if(/novogene\.com|novocloud|novo\.?cloud/i.test(u)) return 'NovoCloud';
      return 'Unknown';},
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
    },
    filteredJobs(){
      if(this.statusFilter==='all') return this.jobs
      return this.jobs.filter(j=>j.task_status===this.statusFilter)
    }
  },
  methods:{
    focusUrlInput(){
      try{ this.$refs.urlInput && this.$refs.urlInput.focus() }catch(e){}
      try{ window.scrollTo({top:0,behavior:'smooth'}) }catch(e){}
    },
    async acceptSharedFile(fileId){
      try{
        const token = localStorage.getItem('token')
        if(!token){ this.msg='请先登录'; this.err=true; return }
        const targetFolderId = this._resolveSelectedFolderId()
        const {data} = await axios.post('/api/files/accept/file/', { file_id: fileId, target_folder_id: targetFolderId })
        this.msg = '已保存到我的文件'
        this.err = false
      }catch(e){
        this.err = true
        this.msg = e?.response?.data?.detail || '保存失败'
      }
    },
    async acceptSharedFolder(folderId){
      try{
        const token = localStorage.getItem('token')
        if(!token){ this.msg='请先登录'; this.err=true; return }
        const targetFolderId = this._resolveSelectedFolderId()
        const {data} = await axios.post('/api/files/accept/folder/', { folder_id: folderId, target_folder_id: targetFolderId })
        this.msg = '文件夹已保存到我的文件'
        this.err = false
      }catch(e){
        this.err = true
        this.msg = e?.response?.data?.detail || '保存失败'
      }
    },
    async autoDownloadFileById(fileId){
      try{
        const token = localStorage.getItem('token')
        if(!token){ this.msg='Please log in first'; this.err=true; return }
        const res = await fetch(`/api/files/${fileId}/download/`, { headers: { 'Authorization': `Token ${token}` } })
        if(!res.ok){ this.msg='Download failed'; this.err=true; return }
        const blob = await res.blob()
        const cd = res.headers.get('content-disposition') || ''
        let filename = `file_${fileId}`
        const m = cd.match(/filename\*=UTF-8''([^;\n]+)/) || cd.match(/filename="([^"]+)"/)
        if(m){ filename = decodeURIComponent(m[1] || m[0]) }
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        this.msg='Download started'; this.err=false
      }catch(e){ this.msg='Download failed'; this.err=true }
    },
    async autoDownloadFolderById(folderId){
      try{
        const token = localStorage.getItem('token')
        if(!token){ this.msg='Please log in first'; this.err=true; return }
        const res = await fetch(`/file_download/download/folder/${folderId}/`, { headers: { 'Authorization': `Token ${token}`, 'Accept': 'application/zip' } })
        if(!res.ok){ this.msg='Download failed'; this.err=true; return }
        const blob = await res.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `folder_${folderId}.zip`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
        this.msg='Download started'; this.err=false
      }catch(e){ this.msg='Download failed'; this.err=true }
    },
    tryAutoDownloadFromLink(link){
      try{
        const u = new URL(link, window.location.origin)
        const fileId = u.searchParams.get('file')
        const folderId = u.searchParams.get('folder')
        const accept = u.searchParams.get('accept')
        if(fileId || folderId){
          // 站内分享链接默认保存；外站则保持原逻辑
          if(u.origin === window.location.origin){
            if(accept === '0'){
              if(fileId){ this.autoDownloadFileById(Number(fileId)); return true }
              if(folderId){ this.autoDownloadFolderById(Number(folderId)); return true }
            } else {
              if(fileId){ this.acceptSharedFile(Number(fileId)); return true }
              if(folderId){ this.acceptSharedFolder(Number(folderId)); return true }
            }
          } else {
            if(accept === '1'){
              if(fileId){ this.acceptSharedFile(Number(fileId)); return true }
              if(folderId){ this.acceptSharedFolder(Number(folderId)); return true }
            } else {
              if(fileId){ this.autoDownloadFileById(Number(fileId)); return true }
              if(folderId){ this.autoDownloadFolderById(Number(folderId)); return true }
            }
          }
        }
      }catch(e){}
      return false
    },
    openOutdirDialog(){
      this.tmpOutdir = this.outdir || 'downloads'
      this.selectedFolderPath = ''
      this.showOutdirDialog = true
      if(!this.folderOptions.length){ this.fetchFolders() }
    },
    async fetchFolders(){
      try{
        const {data} = await axios.get('/api/files/folders/all/')
        const arr = (data && data.folders) ? data.folders : []
        // 仅保留必要字段
        this.folderOptions = arr.map(f => ({ id: f.id, name: f.name, folder_path: f.folder_path }))
      }catch(e){
        // 忽略错误，保持空列表
        this.folderOptions = []
      }
    },
    _resolveSelectedFolderId(){
      const sel = this.selectedFolderPath
      if(!sel) return null
      const hit = this.folderOptions.find(f => f.folder_path === sel)
      return hit ? hit.id : null
    },
    _resolveSelectedFolderId(){
      const sel = this.selectedFolderPath
      if(!sel || sel==='downloads') return null
      const hit = this.folderOptions.find(f => f.folder_path === sel)
      return hit ? hit.id : null
    },
    async createFolder(){
      this.folderCreateError=''
      const name = (this.newFolderName||'').trim()
      if(!name) return
      const parentId = this._resolveSelectedFolderId()
      this.creating = true
      try{
        const {data} = await axios.post('/api/files/folders/', { name, parent: parentId })
        // 返回的是新文件夹的完整信息（含 folder_path）
        if(data && data.id){
          const f = { id: data.id, name: data.name, folder_path: data.folder_path }
          this.folderOptions.push(f)
          this.selectedFolderPath = data.folder_path
          this.outdir = data.folder_path
          this.newFolderName=''
          this.showCreateInput=false
        } else {
          this.folderCreateError = 'Created successfully but response is unexpected'
        }
      }catch(e){
        this.folderCreateError = e?.response?.data?.error || e?.response?.data?.detail || 'Create failed'
      }finally{
        this.creating = false
      }
    },
    hideCreateInput(){
      this.showCreateInput=false
      this.newFolderName=''
      this.folderCreateError=''
    },
    confirmOutdir(){
      this.outdir = (this.selectedFolderPath || 'downloads')
      this.showOutdirDialog = false
      this.start()
    },
    cancelOutdir(){
      this.showOutdirDialog = false
    },
    async start(){
      this.msg='';this.err=false;this.loading=true;this.progressVisible=false;this.progress=0;this.logPath='';
      try{
        const folderId = this._resolveSelectedFolderId()
        const payload = { url: this.url, outdir: (this.outdir||'downloads') }
        if (folderId) payload.folder_id = folderId
        const {data}=await axios.post('/api/downloads/start/', payload);
        try{localStorage.setItem('downloadOutdir', this.outdir||'downloads')}catch(e){}
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
      // 使用箭头函数保持 this 指向组件实例，避免 setInterval 丢失 this
      this.poller=setInterval(() => { this.pollOnce() }, this.pollIntervalMs);
      this.pollOnce();
    },
    async pollOnce(){
      if(!this.logPath) return;
      if(this.debug) console.log('[pollOnce] this=', this);
      try{
        const {data}=await axios.get('/api/downloads/status/',{params:{log:this.logPath,n:50}});
        if(this.debug) console.log('[status]', data);
        // Prefer provided percent; if missing or zero, fall back to bytes ratio
        let p = parseFloat(data?.percent);
        // 平滑处理：若新值低于当前值，且差距不大（<15%），保留当前值，避免抖动；
        // 同时对突升（>20%）做缓动，限制单次最大增幅为 15%
        if(!Number.isNaN(p)){
          const delta = p - this.progress
          if(delta < 0 && Math.abs(delta) <= 15){
            p = this.progress
          } else if (delta > 20) {
            p = this.progress + 15
          }
        }
        if(Number.isNaN(p) || p === 0){
          const downloaded = Number(data?.downloaded_bytes) || 0;
          const total = Number(data?.total_bytes) || 0;
          if(total > 0){
            p = (downloaded / total) * 100;
          } else if(Number.isNaN(p)) {
            p = 0;
          }
        }
        p = Math.max(0, Math.min(100, p));
        // 若已检测到完成标志但百分比仍为99，强制置为100
        if(Array.isArray(data?.lines) && data.lines.some(l => typeof l==='string' && l.includes('Completed 100%'))){
          p = 100
        }
        if(this.debug) console.log('[set progress]', p);
        this.progress = p;
        if(this.debug) console.log('[current progress]', this.progress);
        this.speedBps = data?.speed_bps || 0;
        this.etaSeconds = (data?.eta_seconds ?? null);
        // Surface backend messages when there are permission errors
        const lines = data?.lines || [];
        if(this.debug && Array.isArray(lines) && lines.length){
          console.log('[messages]', lines);
        }
        if(Array.isArray(lines) && lines.some(x => typeof x === 'string' && /Permission denied/i.test(x))){
          this.err = true;
          this.msg = 'Permission denied starting downloader. Please fix executable permissions.';
        }
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
    async refreshJobs(){
      try{
        this.jobsLoading = true
        const {data} = await axios.get('/api/downloads/jobs/')
        this.jobs = Array.isArray(data?.jobs) ? data.jobs : []
      }catch(e){
        this.jobs = []
      }finally{
        this.jobsLoading = false
        this.updateRunningProgress()
      }
    },
    beginJobsPolling(){
      if(this.jobsPoller) clearInterval(this.jobsPoller)
      this.jobsPoller = setInterval(() => { this.refreshJobs() }, 3000)
    },
    statusText(s){
      if(s===0) return '待处理'
      if(s===1) return '进行中'
      if(s===2) return '完成'
      if(s===3) return '失败'
      return ''
    },
    statusClass(s){
      if(s===0) return 'badge-pending'
      if(s===1) return 'badge-running'
      if(s===2) return 'badge-success'
      if(s===3) return 'badge-failed'
      return ''
    },
    formatTime(t){
      try{
        const d = new Date(t)
        const y = d.getFullYear()
        const m = String(d.getMonth()+1).padStart(2,'0')
        const dd = String(d.getDate()).padStart(2,'0')
        const hh = String(d.getHours()).padStart(2,'0')
        const mm = String(d.getMinutes()).padStart(2,'0')
        return `${y}-${m}-${dd} ${hh}:${mm}`
      }catch(e){return ''}
    },
    async viewLogs(j){
      if(!j?.id) return
      await this.toggleDetails(j)
    },
    async retryJob(j){
      if(!j?.id) return
      try{
        await axios.post(`/api/downloads/jobs/${j.id}/retry/`)
        this.refreshJobs()
      }catch(e){}
    },
    async cancelJob(j){
      if(!j?.id) return
      try{
        await axios.post(`/api/downloads/jobs/${j.id}/cancel/`)
        this.refreshJobs()
      }catch(e){}
    },
    async deleteJob(j){
      if(!j?.id) return
      try{
        await axios.delete(`/api/downloads/jobs/${j.id}/delete/`)
        this.refreshJobs()
      }catch(e){
        const msg = e?.response?.data?.detail || e?.response?.data?.message || '删除失败'
        alert(msg)
      }
    },
    async toggleDetails(j){
      const id = j?.id
      if(!id) return
      const cur = !!this.expandedJobs[id]
      this.$set ? this.$set(this.expandedJobs, id, !cur) : (this.expandedJobs[id] = !cur)
      if(this.expandedJobs[id] && !this.jobLogs[id]){
        this.$set ? this.$set(this.loadingLogs, id, true) : (this.loadingLogs[id] = true)
        try{
          const {data} = await axios.get(`/api/downloads/jobs/${id}/logs/`, { params: { n: 200 } })
          const text = data?.text || ''
          this.$set ? this.$set(this.jobLogs, id, text) : (this.jobLogs[id] = text)
          const percent = Number(data?.percent) || 0
          this.$set ? this.$set(this.jobProgress, id, percent) : (this.jobProgress[id] = percent)
        }catch(e){
          this.$set ? this.$set(this.jobLogs, id, '') : (this.jobLogs[id] = '')
        }finally{
          this.$set ? this.$set(this.loadingLogs, id, false) : (this.loadingLogs[id] = false)
        }
      }
    },
    async updateRunningProgress(){
      const running = (this.jobs||[]).filter(j=>j.task_status===1)
      const limited = running.slice(0,5)
      await Promise.allSettled(limited.map(async j=>{
        try{
          const {data} = await axios.get(`/api/downloads/jobs/${j.id}/logs/`, { params: { n: 20 } })
          const percent = Number(data?.percent) || 0
          this.$set ? this.$set(this.jobProgress, j.id, percent) : (this.jobProgress[j.id] = percent)
        }catch(e){}
      }))
    }
  }
}
</script>
<style scoped>
.download-page{width:100%;min-height:calc(100vh - 72px);padding:8px 12px;background:#fff;--primary: rgb(58, 126, 185);--primary-hover: rgb(45, 102, 150);display:flex;justify-content:center;align-items:flex-start;box-sizing:border-box}
.content-layout{display:grid;grid-template-columns: 2fr 1fr;gap:16px;width:100%;max-width:1600px}
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
  max-width: 100%;
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
  display:inline-flex;
  align-items:center;
  justify-content:center;
  height:56px;
  padding:0 20px;
  border-radius: var(--radius-sm);
  background: var(--primary, rgb(58, 126, 185));
  color:#fff;
  border:1px solid var(--primary, rgb(58, 126, 185));
  font-weight:600;
  line-height:1 !important; /* 强制覆盖全局行高 */
  white-space: nowrap;
}
.btn.sm{ height:32px; padding:0 12px; font-size:13px; line-height:32px !important; min-width:64px }
.btn:not(:disabled):hover{ background: var(--primary-hover, rgb(45, 102, 150)); border-color: var(--primary-hover, rgb(45, 102, 150)); }
.btn:disabled{opacity:.6;cursor:not-allowed}
.btn.cancel{ background: var(--waves-error-600, #b91c1c); border-color: var(--waves-error-600, #b91c1c); height:28px; padding:0 12px; font-size:12px; line-height:28px !important; min-width:64px }
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

/* 选择输出目录弹窗 */
.dialog-backdrop{position:fixed;inset:0;background:rgba(17,24,39,.4);display:flex;align-items:center;justify-content:center;z-index:9999}
.dialog{background:#fff;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,.15);width:520px;max-width:90vw;padding:18px}
.dialog-title{margin:0 0 12px 0;font-size:18px;font-weight:650;color:#1f2937}
.dialog-body{display:flex;flex-direction:column;gap:8px}
.dialog-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}
.btn.secondary{background:#fff;color:#374151;border:1px solid #cbd5e1}
.btn.secondary:hover{background:#f3f4f6}

/* 创建行布局与间距 */
.create-row{ display:flex; align-items:center; gap:10px; }
.create-label{ width:160px; color:#6b7280; font-size:13px }
.create-row .input{ flex:1 }

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
/* Jobs panel styles */
.jobs-panel{background:#fff;border-radius:var(--radius-sm);border:1px solid var(--waves-border-subtle, #cbd5e1);padding:12px;min-height:760px}
.jobs-header{display:flex;flex-direction:column;gap:10px}
.jobs-actions{display:flex;align-items:center;gap:12px}
.jobs-filter{display:flex;align-items:center;gap:10px}
.filter-btn{height:28px;padding:0 12px;border-radius:999px;border:1px solid var(--waves-border-subtle, #e5e7eb);background:#fff;color:#374151;font-size:12px}
.filter-btn.active{background:#f3f4f6}
.jobs-list{margin-top:10px}
.jobs-empty{color:#6b7280;font-size:13px;padding:8px}
.jobs-items{display:flex;flex-direction:column;gap:14px}
.job-item{display:flex;flex-direction:column;gap:10px;border:1px solid var(--waves-border-subtle, #e5e7eb);padding:12px;border-radius:12px;background:#fff;box-shadow:0 2px 8px rgba(27,44,72,0.06)}
.job-card-top{display:flex;align-items:center;justify-content:space-between}
.job-main{display:flex;flex-direction:column;gap:4px}
.job-name{font-size:14px;font-weight:600;color:#111827}
.job-meta{font-size:12px;color:#6b7280}
.job-right{display:flex;align-items:center;gap:12px}
.job-actions{display:flex;align-items:center;gap:12px;flex-wrap:nowrap}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px}
.badge-pending{background:#f3f4f6;color:#374151}
.badge-running{background:#dbeafe;color:#1d4ed8}
.badge-success{background:#dcfce7;color:#16a34a}
.badge-failed{background:#fee2e2;color:#b91c1c}
.job-details{border-top:1px dashed rgba(27,44,72,0.12);padding-top:10px}
.job-details-body{max-height:220px;overflow:auto}
.job-logs{white-space:pre-wrap;font-size:12px;color:#374151}
.mini-progress{width:200px;height:6px;background:#e5e7eb;border-radius:6px;overflow:hidden}
.mini-progress-bar{height:100%;background:var(--primary, rgb(58, 126, 185));transition:width .2s linear}
</style>
