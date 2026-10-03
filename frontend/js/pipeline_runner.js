class PipelineRunner {
  constructor() {
    this.modalOverlay = document.getElementById('pipeline-modal');
    this.stageText = document.getElementById('celery-stage-text');
    this.progressBar = document.getElementById('celery-progress-bar');
    this.progressPercentage = document.getElementById('celery-progress-percentage');
    this.statusText = document.getElementById('pipeline-status-text');
    this.readyToast = document.getElementById('ready-toast');
  }

  async executePipeline(requestData, onCompleted) {
    this.showModal();
    this.resetProgress();

    try {
      this.statusText.innerText = "Submitting task to Celery workers...";

      const response = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData)
      });

      if (!response.ok) {
        throw new Error(`Pipeline failed with HTTP ${response.status}`);
      }

      const { task_id } = await response.json();
      
      // Start polling
      this.pollTaskStatus(task_id, onCompleted);

    } catch (err) {
      console.error(err);
      this.statusText.innerText = `Error: ${err.message}`;
      alert(`Pipeline execution error: ${err.message}`);
    }
  }

  pollTaskStatus(taskId, onCompleted) {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/pipeline/status/${taskId}`);
        const data = await response.json();

        if (data.state === 'PROGRESS' || data.state === 'PENDING') {
            this.stageText.innerText = data.stage || 'Pending in queue...';
            const prog = data.progress || 0;
            this.progressBar.style.width = `${prog}%`;
            this.progressPercentage.innerText = `${prog}%`;
        } else if (data.state === 'SUCCESS') {
            clearInterval(pollInterval);
            this.stageText.innerText = 'Completed!';
            this.progressBar.style.width = '100%';
            this.progressPercentage.innerText = '100%';
            
            setTimeout(() => {
                this.hideModal();
                this.showReadyToast(data.result.summary);
                if (onCompleted) {
                    onCompleted(data.result);
                }
            }, 800);
        } else if (data.state === 'FAILURE') {
            clearInterval(pollInterval);
            this.statusText.innerText = "Task Failed";
            this.stageText.innerText = `Error: ${data.status}`;
            this.progressBar.style.background = '#ef4444';
        }
      } catch (err) {
        console.error("Polling error", err);
      }
    }, 1000);
  }

  showModal() {
    if (this.modalOverlay) this.modalOverlay.classList.add('active');
  }

  hideModal() {
    if (this.modalOverlay) this.modalOverlay.classList.remove('active');
  }

  showReadyToast(summary) {
    if (!this.readyToast) return;
    this.readyToast.innerHTML = `
      <svg viewBox="0 0 20 20" fill="currentColor" width="18" height="18">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
      </svg>
      <div>
        <strong>3D Cadastre Ready!</strong>
        <span style="font-size: 12px; margin-left: 8px;">${summary ? summary.buildings_detected : 0} Buildings &bull; ${summary ? summary.legal_space_units_minted : 0} Legal Units Minted</span>
      </div>
    `;
    this.readyToast.classList.add('show');
    setTimeout(() => {
      this.readyToast.classList.remove('show');
    }, 4500);
  }

  resetProgress() {
    if (this.stageText) this.stageText.innerText = 'Initializing...';
    if (this.progressBar) {
        this.progressBar.style.width = '0%';
        this.progressBar.style.background = 'var(--gradient-neon)';
    }
    if (this.progressPercentage) this.progressPercentage.innerText = '0%';
  }
}
