export default function GuidePage() {
  return (
    <div className="p-8 bg-workday-panel h-full overflow-y-auto">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-4xl font-serif font-semibold text-workday-text mb-2">使用指南</h1>
          <p className="text-workday-muted">了解 Workday 如何帮助你追踪和分析工作时间</p>
        </div>

        {/* What is Workday */}
        <section className="bg-white rounded-lg p-8 shadow-sm mb-6">
          <h2 className="text-2xl font-semibold text-workday-text mb-4 flex items-center gap-2">
            <span>💡</span>
            <span>Workday 是什么？</span>
          </h2>
          <div className="text-workday-muted space-y-3">
            <p>
              Workday 是一个基于 AI 的工作时间追踪工具，灵感来自 <a href="https://github.com/dayflow-ai/dayflow" target="_blank" className="text-blue-500 hover:underline">Dayflow</a>。
            </p>
            <p>
              它会在后台自动录制你的屏幕（1 帧/秒），然后使用 AI 分析你的活动，生成详细的时间线。
            </p>
            <p className="font-medium text-workday-text">
              📌 核心理念：无需手动记录，让 AI 自动理解你的工作内容。
            </p>
          </div>
        </section>

        {/* How it works */}
        <section className="bg-white rounded-lg p-8 shadow-sm mb-6">
          <h2 className="text-2xl font-semibold text-workday-text mb-6 flex items-center gap-2">
            <span>⚙️</span>
            <span>工作原理</span>
          </h2>

          <div className="space-y-6">
            {/* Step 1 */}
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold">
                1
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-workday-text mb-2">🎬 屏幕录制</h3>
                <p className="text-workday-muted mb-3">
                  系统以 <strong>1 帧/秒</strong> 的速率录制屏幕，每 <strong>15 秒</strong>保存为一个视频片段（chunk）。
                </p>
                <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm">
                  <div className="text-gray-600">录制设置：</div>
                  <div className="text-gray-800 mt-1">• 截图间隔：1 秒</div>
                  <div className="text-gray-800">• 片段时长：15 秒</div>
                  <div className="text-gray-800">• 视频质量：85%</div>
                  <div className="text-gray-800">• 编码格式：H.264（浏览器兼容）</div>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-green-100 rounded-full flex items-center justify-center text-green-600 font-bold">
                2
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-workday-text mb-2">🔄 视频合并</h3>
                <p className="text-workday-muted mb-3">
                  每隔 <strong>15 分钟</strong>，系统会将多个小片段合并成一个批次（batch）视频。
                </p>
                <div className="bg-gray-50 rounded-lg p-4 font-mono text-sm">
                  <div className="text-gray-600">15 秒片段 × 60 = 15 分钟批次视频</div>
                  <div className="text-gray-500 mt-2">
                    例如：13:00:00 - 13:15:00 的所有片段 → batch_20251121_130000.mp4
                  </div>
                </div>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-purple-100 rounded-full flex items-center justify-center text-purple-600 font-bold">
                3
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-workday-text mb-2">🤖 AI 分析（两阶段）</h3>
                <p className="text-workday-muted mb-3">
                  使用火山引擎 ARK API 进行两阶段 LLM 分析：
                </p>

                <div className="mb-3 bg-amber-50 border-l-4 border-amber-400 p-3 rounded">
                  <div className="font-semibold text-amber-900 mb-1">📋 模型要求</div>
                  <p className="text-sm text-amber-800 mb-1">
                    必须使用支持<strong>多模态视频输入</strong>的 LLM 模型
                  </p>
                  <ul className="text-xs text-amber-700 list-disc list-inside ml-2 space-y-1">
                    <li>推荐模型：<code className="bg-amber-100 px-1 py-0.5 rounded">doubao-seed-1.6-flash</code></li>
                    <li>模型必须能够处理视频帧（multimodal video input）</li>
                    <li>可在 Settings 页面动态切换模型，无需重启</li>
                  </ul>
                </div>

                <div className="space-y-3">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <div className="font-semibold text-blue-900 mb-2">📝 阶段 1：视频转录</div>
                    <p className="text-sm text-blue-800 mb-2">
                      AI 观看 15 分钟视频，生成 3-5 条观察记录（Observations）
                    </p>
                    <div className="text-xs text-blue-700 font-mono bg-blue-100 rounded p-2">
                      输入：15 分钟视频 → 输出：时间戳 + 活动描述
                    </div>
                  </div>

                  <div className="bg-green-50 rounded-lg p-4">
                    <div className="font-semibold text-green-900 mb-2">🎴 阶段 2：生成活动卡片</div>
                    <p className="text-sm text-green-800 mb-2">
                      AI 基于观察记录，生成时间线卡片（Timeline Cards）
                    </p>
                    <div className="text-xs text-green-700 font-mono bg-green-100 rounded p-2">
                      输入：观察记录 → 输出：标题 + 详细描述 + 分类
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Step 4 */}
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center text-orange-600 font-bold">
                4
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-workday-text mb-2">📊 时间线展示</h3>
                <p className="text-workday-muted mb-3">
                  在 Timeline 页面查看你的工作时间线，点击卡片可以：
                </p>
                <ul className="list-disc list-inside text-workday-muted space-y-1 ml-4">
                  <li>查看详细的活动描述</li>
                  <li>播放对应时间段的录屏视频</li>
                  <li>了解每个活动的时长和分类</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* Data Flow Diagram */}
        <section className="bg-white rounded-lg p-8 shadow-sm mb-6">
          <h2 className="text-2xl font-semibold text-workday-text mb-6 flex items-center gap-2">
            <span>📈</span>
            <span>数据流程图</span>
          </h2>
          <div className="bg-gray-900 text-gray-100 rounded-lg p-6 font-mono text-sm overflow-x-auto">
            <pre className="whitespace-pre">
{`┌──────────────┐
│  屏幕录制     │  每秒截图
│  1 FPS       │────────────┐
└──────────────┘            │
                            ▼
                   ┌──────────────────┐
                   │  15秒视频片段     │
                   │  chunk_xxx.mp4   │
                   └──────────────────┘
                            │
                            │ 每 15 分钟
                            ▼
                   ┌──────────────────┐
                   │  合并批次视频     │
                   │  batch_xxx.mp4   │
                   └──────────────────┘
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
        ┌─────────────────┐   ┌─────────────────┐
        │  阶段1: LLM      │   │  阶段2: LLM      │
        │  视频 → 观察记录  │──▶│  观察 → 活动卡片  │
        └─────────────────┘   └─────────────────┘
                                        │
                                        ▼
                               ┌─────────────────┐
                               │  时间线展示      │
                               │  Timeline Cards │
                               └─────────────────┘`}
            </pre>
          </div>
        </section>

        {/* How to use */}
        <section className="bg-white rounded-lg p-8 shadow-sm mb-6">
          <h2 className="text-2xl font-semibold text-workday-text mb-6 flex items-center gap-2">
            <span>🚀</span>
            <span>快速开始</span>
          </h2>

          <div className="space-y-4">
            <div className="border-l-4 border-blue-500 bg-blue-50 p-4 rounded">
              <div className="font-semibold text-blue-900 mb-2">1️⃣ 配置 API Key</div>
              <p className="text-sm text-blue-800">
                前往 <strong>Settings</strong> 页面，填入你的火山引擎 ARK API Key。
                <br />
                <a href="https://console.volcengine.com/ark" target="_blank" className="text-blue-600 hover:underline">
                  → 获取 API Key
                </a>
              </p>
            </div>

            <div className="border-l-4 border-green-500 bg-green-50 p-4 rounded">
              <div className="font-semibold text-green-900 mb-2">2️⃣ 开始录制</div>
              <p className="text-sm text-green-800">
                点击右上角的 <strong>"Start Recording"</strong> 按钮，系统会开始录制你的屏幕。
              </p>
            </div>

            <div className="border-l-4 border-purple-500 bg-purple-50 p-4 rounded">
              <div className="font-semibold text-purple-900 mb-2">3️⃣ 等待分析</div>
              <p className="text-sm text-purple-800">
                录制 15 分钟后，AI 会自动分析并生成时间线卡片。
                <br />
                你可以在 <strong>Timeline</strong> 页面查看结果。
              </p>
            </div>

            <div className="border-l-4 border-orange-500 bg-orange-50 p-4 rounded">
              <div className="font-semibold text-orange-900 mb-2">4️⃣ 查看统计</div>
              <p className="text-sm text-orange-800">
                在 <strong>Dashboard</strong> 页面查看 Token 使用记录和统计信息。
              </p>
            </div>
          </div>
        </section>

        {/* Features */}
        <section className="bg-white rounded-lg p-8 shadow-sm mb-6">
          <h2 className="text-2xl font-semibold text-workday-text mb-6 flex items-center gap-2">
            <span>✨</span>
            <span>核心功能</span>
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="border border-gray-200 rounded-lg p-4">
              <div className="text-xl mb-2">🎥</div>
              <h3 className="font-semibold text-workday-text mb-1">自动录制</h3>
              <p className="text-sm text-workday-muted">
                低资源占用的屏幕录制，1 FPS 采样率
              </p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <div className="text-xl mb-2">🤖</div>
              <h3 className="font-semibold text-workday-text mb-1">AI 分析</h3>
              <p className="text-sm text-workday-muted">
                两阶段 LLM 分析，生成精准的活动描述
              </p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <div className="text-xl mb-2">📊</div>
              <h3 className="font-semibold text-workday-text mb-1">时间线可视化</h3>
              <p className="text-sm text-workday-muted">
                清晰的时间线展示，支持视频回放
              </p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <div className="text-xl mb-2">⚙️</div>
              <h3 className="font-semibold text-workday-text mb-1">灵活配置</h3>
              <p className="text-sm text-workday-muted">
                支持运行时配置更新，无需重启服务
              </p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <div className="text-xl mb-2">🔒</div>
              <h3 className="font-semibold text-workday-text mb-1">本地存储</h3>
              <p className="text-sm text-workday-muted">
                所有数据存储在本地，保护隐私安全
              </p>
            </div>

            <div className="border border-gray-200 rounded-lg p-4">
              <div className="text-xl mb-2">🐛</div>
              <h3 className="font-semibold text-workday-text mb-1">调试模式</h3>
              <p className="text-sm text-workday-muted">
                跳过 LLM 调用，节省 Token 用于测试
              </p>
            </div>
          </div>
        </section>

        {/* Categories */}
        <section className="bg-white rounded-lg p-8 shadow-sm mb-6">
          <h2 className="text-2xl font-semibold text-workday-text mb-6 flex items-center gap-2">
            <span>🏷️</span>
            <span>活动分类</span>
          </h2>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded-lg">
              <div className="text-3xl mb-2">💼</div>
              <div className="font-semibold text-blue-900">工作</div>
              <div className="text-xs text-blue-700 mt-1">编程、会议、文档</div>
            </div>

            <div className="text-center p-4 bg-green-50 rounded-lg">
              <div className="text-3xl mb-2">📚</div>
              <div className="font-semibold text-green-900">学习</div>
              <div className="text-xs text-green-700 mt-1">阅读、教程、研究</div>
            </div>

            <div className="text-center p-4 bg-yellow-50 rounded-lg">
              <div className="text-3xl mb-2">🎮</div>
              <div className="font-semibold text-yellow-900">娱乐</div>
              <div className="text-xs text-yellow-700 mt-1">游戏、视频、社交</div>
            </div>

            <div className="text-center p-4 bg-gray-50 rounded-lg">
              <div className="text-3xl mb-2">📦</div>
              <div className="font-semibold text-gray-900">其他</div>
              <div className="text-xs text-gray-700 mt-1">未分类活动</div>
            </div>
          </div>
        </section>

        {/* Tips */}
        <section className="bg-white rounded-lg p-8 shadow-sm mb-6">
          <h2 className="text-2xl font-semibold text-workday-text mb-6 flex items-center gap-2">
            <span>💡</span>
            <span>使用技巧</span>
          </h2>

          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="text-green-500 mt-1">✓</div>
              <div className="flex-1">
                <p className="text-workday-text">
                  <strong>选择合适的显示器：</strong> 在设置中可以选择录制所有显示器或单个显示器
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="text-green-500 mt-1">✓</div>
              <div className="flex-1">
                <p className="text-workday-text">
                  <strong>调试模式：</strong> 测试时开启调试模式可以跳过 LLM 调用，节省 Token
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="text-green-500 mt-1">✓</div>
              <div className="flex-1">
                <p className="text-workday-text">
                  <strong>数据清理：</strong> 定期清理旧数据可以释放存储空间
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="text-green-500 mt-1">✓</div>
              <div className="flex-1">
                <p className="text-workday-text">
                  <strong>Token 监控：</strong> 在 Header 和 Dashboard 中查看 Token 使用情况
                </p>
              </div>
            </div>

            <div className="flex items-start gap-3">
              <div className="text-green-500 mt-1">✓</div>
              <div className="flex-1">
                <p className="text-workday-text">
                  <strong>配置即时生效：</strong> 修改模型 ID 等配置后无需重启服务
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="bg-white rounded-lg p-8 shadow-sm mb-6">
          <h2 className="text-2xl font-semibold text-workday-text mb-6 flex items-center gap-2">
            <span>❓</span>
            <span>常见问题</span>
          </h2>

          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-workday-text mb-2">Q: 录制会影响电脑性能吗？</h3>
              <p className="text-workday-muted text-sm">
                A: 不会。系统采用 1 FPS 的采样率，资源占用非常低，对日常工作几乎没有影响。
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-workday-text mb-2">Q: 我的数据安全吗？</h3>
              <p className="text-workday-muted text-sm">
                A: 是的。所有录屏数据都存储在本地，只有需要分析时才会发送到 LLM API。你可以随时删除本地数据。
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-workday-text mb-2">Q: Token 消耗如何计算？</h3>
              <p className="text-workday-muted text-sm">
                A: 每 15 分钟的分析包含两次 LLM 调用：视频转录 + 生成卡片。具体消耗取决于视频内容复杂度。你可以在 Dashboard 查看详细记录。
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-workday-text mb-2">Q: 视频无法播放怎么办？</h3>
              <p className="text-workday-muted text-sm">
                A: 旧版本录制的视频可能使用了不兼容的编码。新版本已使用 H.264 编码，浏览器可以直接播放。旧视频可以使用转码工具转换。
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-workday-text mb-2">Q: 可以自定义分析模型吗？</h3>
              <p className="text-workday-muted text-sm">
                A: 可以。在 Settings 页面修改 Model 配置项，支持所有火山引擎 ARK 兼容的多模态模型。<strong>注意：模型必须支持视频输入</strong>，推荐使用 doubao-seed-1.6-flash 等支持视频理解的模型。配置立即生效，无需重启。
              </p>
            </div>
          </div>
        </section>

        {/* Footer */}
        <div className="text-center py-8 text-sm text-workday-muted">
          <p>
            基于 <a href="https://github.com/dayflow-ai/dayflow" target="_blank" className="text-blue-500 hover:underline">Dayflow</a> 开发
          </p>
          <p className="mt-2">
            使用 Python + FastAPI + Next.js 构建
          </p>
        </div>
      </div>
    </div>
  );
}
