<template>
  <footer class="footer gradient-bg">
    <div class="container footer-grid">
      <div class="footer-col">
        <h3>SmartMall-AI</h3>
        <p>AI 驱动的智能电商平台，融合大模型对话、RAG 商品知识库、协同过滤推荐和实时客服。</p>
      </div>
      <div class="footer-col">
        <h4>快速链接</h4>
        <router-link to="/">首页</router-link>
        <router-link to="/products">全部商品</router-link>
        <router-link to="/ai-chat">AI 助手</router-link>
      </div>
      <div class="footer-col">
        <h4>技术栈</h4>
        <span>FastAPI + Vue 3</span>
        <span>LangChain + DeepSeek</span>
        <span>MySQL + Redis + ChromaDB</span>
        <span>Docker + Nginx</span>
      </div>
      <div class="footer-col">
        <h4>联系方式</h4>
        <a href="https://github.com" target="_blank">GitHub</a>
        <span>SmartMall-AI © 2026</span>
      </div>
    </div>
    <div class="footer-bottom">
      <span>Built with ❤️ for Full-Stack Job Application</span>
    </div>
  </footer>
</template>

<style scoped>
.footer {
  padding: 48px 0 0;
  color: rgba(255,255,255,0.85);
}
.footer-grid {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr;
  gap: 40px;
}
.footer-col h3, .footer-col h4 { color: white; margin-bottom: 12px; }
.footer-col h3 { font-size: 20px; }
.footer-col p { font-size: 13px; line-height: 1.8; color: rgba(255,255,255,0.65); }
.footer-col a, .footer-col span {
  display: block;
  font-size: 13px;
  color: rgba(255,255,255,0.65);
  margin-bottom: 8px;
  transition: color 0.2s;
}
.footer-col a:hover { color: white; }
.footer-bottom {
  text-align: center;
  padding: 20px 0;
  margin-top: 32px;
  border-top: 1px solid rgba(255,255,255,0.1);
  font-size: 12px;
  color: rgba(255,255,255,0.5);
}

@media (max-width: 768px) {
  .footer-grid { grid-template-columns: 1fr 1fr; }
}
</style>
