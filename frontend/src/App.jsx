import React, { useState, useEffect, useRef } from 'react';
import {
  FolderGit2, Activity, Code2, Search,
  GitBranch, Play, CheckCircle2,
  FileText, Shield, Layers, FileCode, Server,
  Terminal, SearchCode, Merge, Check, Info, Box,
  ChevronDown, ChevronRight, Folder, File, AlertCircle,
  GitCommit, RefreshCw, Eye, Sparkles, ExternalLink,
  Cpu, CheckSquare, AlertTriangle, ArrowRight, Copy,
  Upload, GitPullRequest, Settings, Zap, Rocket,
  GitFork, User, Lock, Key, CheckCircle, HelpCircle
} from 'lucide-react';

const API = 'http://localhost:8000/api';

const AGENTS = [
  { key: 'Product Manager', name: 'Product Manager', icon: FileText, color: 'blue', desc: 'Specifications & Acceptance Criteria' },
  { key: 'Architect', name: 'System Architect', icon: Layers, color: 'purple', desc: 'Folder Mapping & Architecture Plan' },
  { key: 'Security', name: 'Security Engineer', icon: Shield, color: 'red', desc: 'AppSec Threat Modeling & Guidelines' },
  { key: 'Developer', name: 'Full-Stack Developer', icon: Code2, color: 'cyan', desc: 'Surgical Code Generation' },
  { key: 'Tester', name: 'QA Test Engineer', icon: CheckCircle2, color: 'green', desc: 'Syntax & Automated Verification' },
  { key: 'Reviewer', name: 'Staff Code Reviewer', icon: SearchCode, color: 'yellow', desc: 'PR Quality Review & Approval' },
  { key: 'DevOps', name: 'DevOps Engineer', icon: Server, color: 'orange', desc: 'CI/CD Pipeline & Deployment' },
];

// === FOLDER TREE COMPONENT ===
function FolderTree({ treeString, onFileClick }) {
  if (!treeString) return <div className="text-xs text-slate-500 p-3">No files indexed</div>;

  const paths = treeString.split('\n').filter(Boolean);
  const tree = {};

  paths.forEach(p => {
    const parts = p.replace(/\\/g, '/').split('/');
    let current = tree;
    parts.forEach((part, i) => {
      if (!current[part]) current[part] = i === parts.length - 1 ? null : {};
      if (current[part] !== null) current = current[part];
    });
  });

  return (
    <div className="space-y-0.5 text-xs font-mono select-none">
      <TreeNode name="Root" node={tree} path="" onFileClick={onFileClick} defaultOpen={true} />
    </div>
  );
}

function TreeNode({ name, node, path, onFileClick, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const isFolder = node !== null && typeof node === 'object';
  const fullPath = path ? `${path}/${name}` : (name === 'Root' ? '' : name);

  if (!isFolder) {
    const ext = name.split('.').pop().toLowerCase();
    const colors = {
      py: 'text-emerald-400', js: 'text-amber-400', jsx: 'text-cyan-400',
      ts: 'text-blue-400', tsx: 'text-sky-400', html: 'text-orange-400',
      css: 'text-pink-400', json: 'text-yellow-300', md: 'text-slate-400',
      sql: 'text-red-400', yml: 'text-purple-400', yaml: 'text-purple-400',
    };
    return (
      <div
        className="flex items-center gap-2 py-1 px-2.5 hover:bg-slate-800/80 rounded-md cursor-pointer group transition-colors"
        onClick={() => onFileClick && onFileClick(fullPath)}
      >
        <File className={`w-3.5 h-3.5 shrink-0 ${colors[ext] || 'text-slate-400'}`} />
        <span className="text-slate-300 group-hover:text-cyan-300 transition-colors truncate">{name}</span>
      </div>
    );
  }

  const entries = Object.entries(node).sort(([, a], [, b]) => {
    const aIsDir = a !== null && typeof a === 'object';
    const bIsDir = b !== null && typeof b === 'object';
    if (aIsDir && !bIsDir) return -1;
    if (!aIsDir && bIsDir) return 1;
    return 0;
  });

  return (
    <div>
      <div
        className="flex items-center gap-1.5 py-1 px-2 hover:bg-slate-800/60 rounded-md cursor-pointer transition-colors"
        onClick={() => setOpen(!open)}
      >
        {open ? <ChevronDown className="w-3.5 h-3.5 text-slate-500 shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500 shrink-0" />}
        <Folder className={`w-4 h-4 shrink-0 ${open ? 'text-cyan-400' : 'text-slate-400'}`} />
        <span className={`text-xs font-semibold truncate ${open ? 'text-white' : 'text-slate-300'}`}>{name}</span>
        <span className="text-[10px] text-slate-600 ml-auto font-mono">{entries.length}</span>
      </div>
      {open && (
        <div className="ml-3 pl-2.5 border-l border-slate-700/60 space-y-0.5 mt-0.5">
          {entries.map(([childName, childNode]) => (
            <TreeNode
              key={childName}
              name={childName}
              node={childNode}
              path={fullPath}
              onFileClick={onFileClick}
              defaultOpen={false}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState('repository');
  const [repoInput, setRepoInput] = useState('c:/Final Year');
  const [repoPath, setRepoPath] = useState('');
  const [error, setError] = useState('');
  const [toast, setToast] = useState('');

  // GitHub Settings & Auth State
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [githubTokenInput, setGithubTokenInput] = useState('');
  const [githubUser, setGithubUser] = useState(null);
  const [githubConfigured, setGithubConfigured] = useState(false);
  const [isSavingToken, setIsSavingToken] = useState(false);

  // Repository Tab State
  const [isScanning, setIsScanning] = useState(false);
  const [metadata, setMetadata] = useState(null);
  const [treeData, setTreeData] = useState(null);
  const [explainer, setExplainer] = useState(null);
  const [gitInfo, setGitInfo] = useState(null);
  const [repoAccess, setRepoAccess] = useState(null);
  const [viewingFile, setViewingFile] = useState(null);
  const [isForking, setIsForking] = useState(false);

  // Pipeline Tab State
  const [taskPrompt, setTaskPrompt] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [agentLogs, setAgentLogs] = useState([]);
  const [pipelineResult, setPipelineResult] = useState(null);
  const [activeAgentIdx, setActiveAgentIdx] = useState(-1);
  const [completedAgents, setCompletedAgents] = useState(new Set());
  const [currentAgent, setCurrentAgent] = useState('');
  const [useStreaming, setUseStreaming] = useState(true);

  // Code Review & Commit State
  const [selectedFile, setSelectedFile] = useState('');
  const [isMerging, setIsMerging] = useState(false);
  const [mergeSuccess, setMergeSuccess] = useState(false);
  const [commitMessage, setCommitMessage] = useState('Autonomous SDLC update via ADT-SE');
  const [isCommitting, setIsCommitting] = useState(false);
  const [commitResult, setCommitResult] = useState(null);

  // GitHub Controls & PR Modal State
  const [isPushing, setIsPushing] = useState(false);
  const [pushResult, setPushResult] = useState(null);
  const [showPRModal, setShowPRModal] = useState(false);
  const [isCreatingPR, setIsCreatingPR] = useState(false);
  const [prResult, setPrResult] = useState(null);
  const [prTitle, setPrTitle] = useState('');
  const [prBody, setPrBody] = useState('');
  const [prBaseBranch, setPrBaseBranch] = useState('main');
  const [prHeadBranch, setPrHeadBranch] = useState('');

  // Deploy & Remote State
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployResult, setDeployResult] = useState(null);
  const [deployBranch, setDeployBranch] = useState(true);
  const [deployPush, setDeployPush] = useState(true);
  const [deployPR, setDeployPR] = useState(true);
  const [deployMode, setDeployMode] = useState('pr'); // 'pr' (industry team review) or 'direct' (personal direct deploy)
  const [showRemoteModal, setShowRemoteModal] = useState(false);
  const [customRemoteInput, setCustomRemoteInput] = useState('');

  // Search Tab State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const showToast = (msg) => {
    setToast(msg);
    setTimeout(() => setToast(''), 4000);
  };

  // --- API Helper ---
  const api = async (method, path, body) => {
    const opts = { method, headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(`${API}${path}`, opts);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.message || 'API Error');
    return data;
  };

  // Check Git & GitHub status on load
  const checkGitStatus = async () => {
    try {
      const gitStatus = await api('GET', '/twin/git/status');
      setGithubConfigured(gitStatus.github_configured || false);
      if (gitStatus.github_user) setGithubUser(gitStatus.github_user);
      if (gitStatus.repo_access) setRepoAccess(gitStatus.repo_access);
      if (gitStatus.git) setGitInfo(gitStatus.git);
    } catch (_) {
      setGithubConfigured(false);
    }
  };

  useEffect(() => {
    checkGitStatus();
  }, []);

  // --- Save / Connect GitHub Token ---
  const handleSaveGitHubToken = async () => {
    setIsSavingToken(true);
    setError('');
    try {
      const res = await api('POST', '/twin/github/setup', { token: githubTokenInput });
      if (res.status === 'success') {
        setGithubConfigured(res.configured);
        setGithubUser(res.username || null);
        showToast(res.message);
        setShowSettingsModal(false);
        checkGitStatus();
      } else {
        setError(res.message || 'Failed to authenticate with GitHub');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingToken(false);
    }
  };

  // --- Scan Repository ---
  const handleScan = async () => {
    if (!repoInput.trim()) return;
    setIsScanning(true);
    setError('');
    try {
      const isGithub = repoInput.includes('github.com');
      let scanData;
      if (isGithub) {
        scanData = await api('POST', '/twin/clone', { github_url: repoInput });
        setRepoPath(scanData.repo_path || repoInput);
      } else {
        scanData = await api('POST', '/twin/scan', { repo_path: repoInput });
        setRepoPath(repoInput);
      }

      const [metaRes, treeRes, explRes] = await Promise.all([
        api('GET', '/twin/metadata'),
        api('GET', '/twin/tree'),
        api('GET', '/explainer/summary'),
      ]);

      setMetadata(metaRes.metadata || metaRes);
      setGitInfo(metaRes.git_info || null);
      setTreeData(treeRes.tree);
      setExplainer(explRes.report);

      await checkGitStatus();
      showToast('Digital Twin initialized & repository analyzed!');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsScanning(false);
    }
  };

  // --- Fork Repository (for external / team-lead repos) ---
  const handleForkRepo = async () => {
    if (!gitInfo?.remote_url) return;
    setIsForking(true);
    setError('');
    try {
      const match = gitInfo.remote_url.match(/github\.com[:/]([^/]+)\/([^/.]+?)(?:\.git)?\/?$/);
      if (!match) throw new Error('Could not parse GitHub repo owner and name from: ' + gitInfo.remote_url);
      const [, owner, repo] = match;

      const res = await api('POST', '/twin/github/fork', { owner, repo });
      showToast(res.message || `Successfully linked to fork @${res.owner}! Remote updated.`);
      await checkGitStatus();
    } catch (err) {
      setError(err.message || 'Fork could not be completed. You can also use Direct Deploy if you are a contributor, or set a custom fork URL.');
    } finally {
      setIsForking(false);
    }
  };

  // --- Manually Set Remote URL (Personal Fork / Contributor) ---
  const handleSetCustomRemote = async (customUrl) => {
    if (!customUrl) return;
    try {
      const res = await api('POST', '/twin/git/set-remote', { remote_url: customUrl });
      showToast(res.message || 'Git remote origin updated successfully!');
      await checkGitStatus();
    } catch (err) {
      setError(err.message);
    }
  };

  // --- View File ---
  const handleFileClick = async (path) => {
    if (!path) return;
    try {
      const data = await api('GET', `/twin/file?path=${encodeURIComponent(path)}`);
      setViewingFile({ path, content: data.content });
    } catch (err) {
      setViewingFile({ path, content: `// Could not read file content: ${err.message}` });
    }
  };

  // --- Run SDLC Pipeline (with SSE streaming) ---
  const handleRunPipeline = async () => {
    if (!repoPath) {
      setError('Please scan or load a repository first!');
      setActiveTab('repository');
      return;
    }
    if (!taskPrompt.trim()) {
      setError('Please describe your SDLC task or feature request!');
      return;
    }

    setIsRunning(true);
    setAgentLogs([]);
    setPipelineResult(null);
    setActiveAgentIdx(0);
    setCompletedAgents(new Set());
    setCurrentAgent('');
    setMergeSuccess(false);
    setCommitResult(null);
    setPushResult(null);
    setPrResult(null);
    setDeployResult(null);
    setError('');

    // Pre-populate PR title
    setPrTitle(`ADT-SE: ${taskPrompt.slice(0, 70)}`);
    const dateTag = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 12);
    setPrHeadBranch(`feature/adt-se-${dateTag}`);

    if (useStreaming) {
      try {
        const response = await fetch(`${API}/agents/run-stream`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ task_prompt: taskPrompt, repo_path: repoPath }),
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.slice(6));
                handleSSEEvent(event);
              } catch (_) { /* skip malformed */ }
            }
          }
        }
      } catch (err) {
        console.warn('SSE failed, falling back to sync execution:', err);
        await runPipelineSync();
      }
    } else {
      await runPipelineSync();
    }

    setIsRunning(false);
  };

  const handleSSEEvent = (event) => {
    const { event: eventType, data } = event;

    switch (eventType) {
      case 'pipeline_start':
        setActiveAgentIdx(0);
        break;

      case 'agent_start': {
        const agentName = data.agent || data.node;
        setCurrentAgent(agentName);
        const idx = AGENTS.findIndex(a => a.key === agentName);
        if (idx >= 0) setActiveAgentIdx(idx);
        break;
      }

      case 'agent_log':
        setAgentLogs(prev => [...prev, {
          agent: data.agent,
          action: data.action,
          output: data.output,
          timestamp: Date.now() / 1000,
        }]);
        break;

      case 'agent_complete': {
        setCompletedAgents(prev => new Set([...prev, data.agent || data.node]));
        const idx = AGENTS.findIndex(a => a.key === (data.agent || data.node));
        if (idx >= 0) setActiveAgentIdx(idx + 1);
        break;
      }

      case 'pipeline_complete':
        setPipelineResult(data);
        setAgentLogs(data.trajectory_logs || []);
        const generatedKeys = Object.keys(data.generated_code || {});
        if (generatedKeys.length > 0) setSelectedFile(generatedKeys[0]);
        setActiveAgentIdx(7);
        showToast(`SDLC Pipeline complete! ${generatedKeys.length} file(s) generated.`);
        break;

      case 'error':
        setError('Pipeline error: ' + (data.message || 'Unknown error'));
        setActiveAgentIdx(7);
        break;

      default:
        break;
    }
  };

  const runPipelineSync = async () => {
    const timer = setInterval(() => {
      setActiveAgentIdx(prev => {
        if (prev < 6) return prev + 1;
        clearInterval(timer);
        return 6;
      });
    }, 2500);

    try {
      const res = await api('POST', '/agents/run', { task_prompt: taskPrompt, repo_path: repoPath });
      setPipelineResult(res);
      setAgentLogs(res.trajectory_logs || []);
      const generatedKeys = Object.keys(res.generated_code || {});
      if (generatedKeys.length > 0) setSelectedFile(generatedKeys[0]);
      showToast(`SDLC Pipeline complete! ${generatedKeys.length} file(s) generated.`);
    } catch (err) {
      setError('Pipeline error: ' + err.message);
    } finally {
      clearInterval(timer);
      setActiveAgentIdx(7);
    }
  };

  // --- Merge to Disk ---
  const handleMerge = async () => {
    if (!pipelineResult?.generated_code) return;
    setIsMerging(true);
    setError('');
    try {
      await api('POST', '/agents/merge', {
        repo_path: repoPath,
        files_to_write: pipelineResult.generated_code
      });
      setMergeSuccess(true);
      showToast('Changes merged to disk & Digital Twin re-indexed!');
      const [metaRes, treeRes] = await Promise.all([
        api('GET', '/twin/metadata'),
        api('GET', '/twin/tree'),
      ]);
      setMetadata(metaRes.metadata || metaRes);
      setTreeData(treeRes.tree);
    } catch (err) {
      setError('Merge failed: ' + err.message);
    } finally {
      setIsMerging(false);
    }
  };

  // --- Git Commit ---
  const handleGitCommit = async () => {
    if (!repoPath) return;
    setIsCommitting(true);
    setError('');
    try {
      const res = await api('POST', '/twin/git/commit', { message: commitMessage });
      setCommitResult(res);
      if (res.status === 'success') {
        showToast(res.committed ? `Committed: ${res.commit_hash}` : 'Working directory clean');
        checkGitStatus();
      } else {
        setError(res.message);
      }
    } catch (err) {
      setError('Git commit failed: ' + err.message);
    } finally {
      setIsCommitting(false);
    }
  };

  // --- Git Push ---
  const handleGitPush = async () => {
    setIsPushing(true);
    setError('');
    try {
      const res = await api('POST', '/twin/git/push', {});
      setPushResult(res);
      if (res.status === 'success') {
        showToast(`Pushed to remote: ${res.branch}`);
        checkGitStatus();
      } else {
        setError(res.message);
      }
    } catch (err) {
      setError('Push failed: ' + err.message);
    } finally {
      setIsPushing(false);
    }
  };

  // --- Open PR Creation Modal ---
  const handleOpenPRModal = () => {
    if (!githubConfigured) {
      setShowSettingsModal(true);
      return;
    }
    if (!prTitle) {
      setPrTitle(`ADT-SE: ${taskPrompt.slice(0, 70) || 'Autonomous Feature Update'}`);
    }
    const currentBranch = gitInfo?.branch || 'main';
    setPrHeadBranch(currentBranch);
    setShowPRModal(true);
  };

  // --- Submit Pull Request ---
  const handleSubmitPR = async () => {
    setIsCreatingPR(true);
    setError('');
    try {
      const res = await api('POST', '/twin/git/pr', {
        title: prTitle,
        body: prBody || 'Auto-generated code changes from the 7-Agent SDLC pipeline.',
        head_branch: prHeadBranch,
        base_branch: prBaseBranch,
      });
      setPrResult(res);
      if (res.status === 'success') {
        showToast(`Pull Request #${res.pr_number} created on GitHub!`);
        setShowPRModal(false);
      } else {
        setError(res.error || 'PR creation failed');
      }
    } catch (err) {
      setError('PR creation failed: ' + err.message);
    } finally {
      setIsCreatingPR(false);
    }
  };

  // --- One-Click Full Deploy Flow ---
  const handleDeploy = async () => {
    if (!pipelineResult?.generated_code) return;
    setIsDeploying(true);
    setError('');
    try {
      const dateTag = new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 12);
      const featureBranch = `feature/adt-se-${dateTag}`;

      const res = await api('POST', '/agents/deploy', {
        repo_path: repoPath,
        files_to_write: pipelineResult.generated_code,
        commit_message: commitMessage,
        create_branch: deployBranch,
        branch_name: featureBranch,
        push_to_github: deployPush,
        create_pr: deployPR,
        pr_title: `ADT-SE: ${taskPrompt.slice(0, 80) || 'Autonomous SDLC Changes'}`,
      });
      setDeployResult(res);
      setMergeSuccess(true);
      showToast('One-Click Deploy pipeline completed!');
      const [metaRes, treeRes] = await Promise.all([
        api('GET', '/twin/metadata'),
        api('GET', '/twin/tree'),
      ]);
      setMetadata(metaRes.metadata || metaRes);
      setTreeData(treeRes.tree);
      checkGitStatus();
    } catch (err) {
      setError('Deploy failed: ' + err.message);
    } finally {
      setIsDeploying(false);
    }
  };

  // --- Semantic Search ---
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setError('');
    try {
      const data = await api('POST', '/twin/search', { query: searchQuery, top_k: 8 });
      setSearchResults(data.results || []);
    } catch (err) {
      setError('Search failed: ' + err.message);
    } finally {
      setIsSearching(false);
    }
  };

  const generatedCode = pipelineResult?.generated_code || {};
  const originalCode = pipelineResult?.original_code || {};
  const generatedFiles = Object.keys(generatedCode);

  const tabs = [
    { id: 'repository', label: 'Repository', icon: FolderGit2, badge: metadata ? `${metadata.total_files || 0} files` : null },
    { id: 'pipeline', label: '7-Agent SDLC', icon: GitBranch, badge: isRunning ? 'Running' : null },
    { id: 'review', label: 'Code Review & Deploy', icon: FileCode, badge: generatedFiles.length ? `${generatedFiles.length} ready` : null },
    { id: 'search', label: 'Semantic Search', icon: Search, badge: null },
  ];

  return (
    <div className="min-h-screen bg-[#070b14] text-slate-100 flex flex-col font-sans antialiased">

      {/* Top Navigation Bar */}
      <header className="glass-panel sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between border-b border-slate-800 bg-[#0c1222]/90 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-cyan-500 via-indigo-500 to-purple-600 rounded-xl shadow-md shadow-cyan-500/20">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold bg-gradient-to-r from-cyan-400 via-teal-300 to-purple-400 bg-clip-text text-transparent">
                ADT-SE
              </h1>
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 rounded-full font-semibold">
                v2.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400">Agentic Digital Twin for Software Engineering</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {repoPath && (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/80 border border-slate-700/80 rounded-lg text-xs font-mono text-slate-300">
              <FolderGit2 className="w-3.5 h-3.5 text-cyan-400" />
              <span className="truncate max-w-xs">{repoPath}</span>
              {gitInfo?.is_git_repo && (
                <span className="ml-1 px-1.5 py-0.5 bg-purple-500/20 text-purple-300 rounded text-[10px]">
                  {gitInfo.branch}
                </span>
              )}
            </div>
          )}

          {/* GitHub Connection Badge & Settings Button */}
          <button
            onClick={() => setShowSettingsModal(true)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition border ${
              githubConfigured
                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/25'
                : 'bg-slate-800/90 text-slate-300 border-slate-700 hover:bg-slate-700/90'
            }`}
          >
            {githubConfigured ? (
              <>
                <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />
                <span>GitHub {githubUser ? `@${githubUser}` : 'Connected'}</span>
              </>
            ) : (
              <>
                <Key className="w-3.5 h-3.5 text-amber-400" />
                <span>Connect GitHub</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* GitHub Settings Modal */}
      {showSettingsModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md rounded-2xl border border-slate-700 bg-[#0c1222] p-6 shadow-2xl space-y-4 animate-in fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Key className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">GitHub Integration Settings</h3>
              </div>
              <button
                onClick={() => setShowSettingsModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <p className="text-slate-300 leading-relaxed">
                Connect your GitHub account to enable <strong>Pushing commits</strong>, <strong>Forking repositories</strong>, and <strong>Creating Pull Requests</strong> for your team lead to review.
              </p>

              {githubConfigured && githubUser && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <User className="w-4 h-4 text-emerald-400" />
                    <div>
                      <div className="font-semibold text-emerald-300">Authenticated as @{githubUser}</div>
                      <div className="text-[10px] text-slate-400">Push, Fork & PR capabilities active</div>
                    </div>
                  </div>
                  <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-mono">ACTIVE</span>
                </div>
              )}

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  GitHub Personal Access Token (PAT)
                </label>
                <input
                  type="password"
                  value={githubTokenInput}
                  onChange={e => setGithubTokenInput(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 font-mono"
                />
                <p className="text-[10px] text-slate-500 mt-1.5 flex items-center gap-1">
                  <HelpCircle className="w-3 h-3" /> Token requires <code className="text-cyan-400 bg-slate-800 px-1 rounded">repo</code> scope for push & PR creation.
                </p>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between">
              {githubConfigured && (
                <button
                  onClick={async () => {
                    await api('POST', '/twin/github/setup', { token: '' });
                    setGithubConfigured(false);
                    setGithubUser(null);
                    showToast('GitHub disconnected');
                  }}
                  className="text-xs text-red-400 hover:text-red-300 underline"
                >
                  Disconnect
                </button>
              )}
              <div className="flex items-center gap-2 ml-auto">
                <button
                  onClick={() => setShowSettingsModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveGitHubToken}
                  disabled={isSavingToken || !githubTokenInput.trim()}
                  className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-500 hover:to-teal-400 text-white font-semibold rounded-xl text-xs disabled:opacity-50 transition shadow-lg shadow-cyan-600/20 flex items-center gap-1.5"
                >
                  {isSavingToken ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <Check className="w-3.5 h-3.5" />}
                  Verify & Connect
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pull Request Configuration Modal */}
      {showPRModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-lg rounded-2xl border border-slate-700 bg-[#0c1222] p-6 shadow-2xl space-y-4 animate-in fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <GitPullRequest className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Create Pull Request for Team Review</h3>
              </div>
              <button
                onClick={() => setShowPRModal(false)}
                className="text-slate-400 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  PR Title
                </label>
                <input
                  type="text"
                  value={prTitle}
                  onChange={e => setPrTitle(e.target.value)}
                  placeholder="e.g. ADT-SE: Implement user authentication endpoint"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-xs text-white focus:outline-none focus:border-cyan-400"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Base Branch (Target)
                  </label>
                  <input
                    type="text"
                    value={prBaseBranch}
                    onChange={e => setPrBaseBranch(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Head Branch (Your Changes)
                  </label>
                  <input
                    type="text"
                    value={prHeadBranch}
                    onChange={e => setPrHeadBranch(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white font-mono text-cyan-300"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Description / Trajectory Summary
                </label>
                <textarea
                  value={prBody}
                  onChange={e => setPrBody(e.target.value)}
                  placeholder="Leave empty to auto-generate a rich 7-Agent SDLC report with acceptance criteria, test outputs, and security checklist..."
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl p-3 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 min-h-[90px] resize-y font-mono"
                />
              </div>

              {repoAccess?.is_fork && (
                <div className="p-2.5 bg-purple-500/10 border border-purple-500/20 rounded-xl text-[11px] text-purple-300 flex items-center gap-2">
                  <GitFork className="w-3.5 h-3.5 shrink-0" />
                  <span>Cross-fork PR will be submitted to upstream repo <strong>{repoAccess.parent}</strong></span>
                </div>
              )}
            </div>

            <div className="pt-2 flex items-center justify-end gap-2">
              <button
                onClick={() => setShowPRModal(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitPR}
                disabled={isCreatingPR || !prTitle.trim()}
                className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold rounded-xl text-xs disabled:opacity-50 transition shadow-lg shadow-cyan-600/20 flex items-center gap-1.5"
              >
                {isCreatingPR ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <GitPullRequest className="w-3.5 h-3.5" />}
                Submit Pull Request to GitHub
              </button>
            </div>
          </div>
        </div>
      )}
      {/* Custom Remote URL Modal */}
      {showRemoteModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-md rounded-2xl border border-slate-700 bg-[#0c1222] p-6 shadow-2xl space-y-4 animate-in fade-in">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <FolderGit2 className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white">Set Target Git Remote URL</h3>
              </div>
              <button onClick={() => setShowRemoteModal(false)} className="text-slate-400 hover:text-white text-sm">✕</button>
            </div>
            <div className="space-y-3 text-xs">
              <p className="text-slate-300">
                Point your workspace git remote directly to your own fork or team repository:
              </p>
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Remote Git URL
                </label>
                <input
                  type="text"
                  value={customRemoteInput}
                  onChange={e => setCustomRemoteInput(e.target.value)}
                  placeholder="https://github.com/your-username/your-repo.git"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
            </div>
            <div className="pt-2 flex items-center justify-end gap-2">
              <button onClick={() => setShowRemoteModal(false)} className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs">
                Cancel
              </button>
              <button
                onClick={async () => {
                  await handleSetCustomRemote(customRemoteInput);
                  setShowRemoteModal(false);
                }}
                disabled={!customRemoteInput.trim()}
                className="px-5 py-2 bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-500 hover:to-teal-400 text-white font-semibold rounded-xl text-xs disabled:opacity-50 transition shadow-lg shadow-cyan-600/20"
              >
                Save Remote
              </button>
            </div>
          </div>
        </div>
      )}


      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-2.5 bg-cyan-600 text-white text-xs font-semibold rounded-xl shadow-xl flex items-center gap-2 animate-in fade-in slide-in-from-bottom-2">
          <Sparkles className="w-4 h-4" /> {toast}
        </div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="bg-red-500/15 border-b border-red-500/40 px-6 py-2.5 flex items-center justify-between text-xs text-red-200">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError('')} className="text-red-400 hover:text-white font-bold ml-4">✕</button>
        </div>
      )}

      {/* Main Workspace Layout */}
      <main className="flex-1 flex overflow-hidden">
        {/* Left Sidebar */}
        <aside className="w-60 glass-panel border-r border-slate-800/80 bg-[#090d19]/80 flex flex-col py-4 shrink-0">
          <nav className="flex-1 px-3 space-y-1.5">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl transition-all text-xs font-medium ${
                  activeTab === tab.id
                    ? 'bg-gradient-to-r from-cyan-500/20 to-purple-500/10 text-cyan-300 font-semibold border border-cyan-500/30 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <tab.icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </div>
                {tab.badge && (
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-md ${
                    activeTab === tab.id ? 'bg-cyan-400/20 text-cyan-200' : 'bg-slate-800 text-slate-500'
                  }`}>
                    {tab.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>

          <div className="px-4 pt-4 border-t border-slate-800/80 text-[11px] text-slate-500">
            <div className="font-semibold text-slate-400">Industry SDLC Workflow</div>
            <div className="text-[10px] text-slate-600 mt-1 leading-relaxed">
              Understand Repo → Generate Code → Verify Architecture → Fork / Push → PR for Team Review
            </div>
          </div>
        </aside>

        {/* Center Workspace Content */}
        <div className="flex-1 overflow-y-auto p-6 bg-[#070b14]">

          {/* ========================================================================= */}
          {/* TAB 1: REPOSITORY UNDERSTANDING & DIGITAL TWIN */}
          {/* ========================================================================= */}
          {activeTab === 'repository' && (
            <div className="max-w-7xl mx-auto space-y-6 animate-in fade-in duration-300">

              {/* Repository Input Header */}
              <div className="glass-card p-5 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <Box className="w-4 h-4 text-cyan-400" /> Target Software Repository
                  </h2>
                  <span className="text-[11px] text-slate-400">Clone company GitHub repo or load local workspace directory</span>
                </div>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={repoInput}
                    onChange={e => setRepoInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleScan()}
                    placeholder="Enter local path (e.g. C:/Final Year) or GitHub URL (https://github.com/org/repo)..."
                    className="flex-1 bg-slate-900/90 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400 transition"
                  />
                  <button
                    onClick={handleScan}
                    disabled={isScanning}
                    className="px-5 py-2.5 bg-gradient-to-r from-cyan-600 to-teal-500 hover:from-cyan-500 hover:to-teal-400 text-white font-semibold rounded-xl disabled:opacity-50 transition shadow-lg shadow-cyan-600/20 flex items-center gap-2 text-xs"
                  >
                    {isScanning ? <Activity className="w-4 h-4 animate-spin" /> : <FolderGit2 className="w-4 h-4" />}
                    {isScanning ? 'Ingesting Codebase...' : 'Scan & Understand'}
                  </button>
                </div>

                {/* Team Collaboration / Fork Assistant Banner */}
                {gitInfo?.remote_url && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between flex-wrap gap-2 text-xs">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">Remote:</span>
                      <span className="font-mono text-cyan-300 font-semibold">{gitInfo.remote_url}</span>
                      {repoAccess && (
                        <span className={`text-[10px] px-2 py-0.5 rounded font-semibold ${
                          repoAccess.can_push ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
                        }`}>
                          {repoAccess.can_push ? 'Direct Push Access' : 'External / Fork Workflow'}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {githubConfigured && repoAccess && !repoAccess.can_push && (
                        <button
                          onClick={handleForkRepo}
                          disabled={isForking}
                          className="px-3 py-1.5 bg-purple-600/20 hover:bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                        >
                          {isForking ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <GitFork className="w-3.5 h-3.5" />}
                          Fork to My Account
                        </button>
                      )}
                      <button
                        onClick={() => {
                          setCustomRemoteInput(gitInfo.remote_url || '');
                          setShowRemoteModal(true);
                        }}
                        className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-1.5 transition"
                      >
                        <FolderGit2 className="w-3.5 h-3.5 text-cyan-400" />
                        Switch Remote
                      </button>
                    </div>
                  </div>
                )}
              </div>

              {/* Metrics Grid */}
              {metadata && (
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
                  {[
                    { label: 'Total Files', value: metadata.total_files || 0, color: 'text-cyan-400' },
                    { label: 'Indexed in Store', value: metadata.indexed_files || metadata.total_files || 0, color: 'text-teal-400' },
                    { label: 'AST Functions', value: metadata.total_functions || 0, color: 'text-purple-400' },
                    { label: 'AST Classes', value: metadata.total_classes || 0, color: 'text-pink-400' },
                    { label: 'API Routes', value: metadata.total_routes || 0, color: 'text-emerald-400' },
                    { label: 'Languages', value: Array.isArray(metadata.languages) ? metadata.languages.length : 0, color: 'text-amber-400' },
                  ].map((s, i) => (
                    <div key={i} className="glass-card p-3 rounded-xl border border-slate-800 bg-[#0e1526]/60 text-center">
                      <div className={`text-xl font-bold ${s.color}`}>{s.value}</div>
                      <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mt-0.5">{s.label}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Main Content Grid: Folder Tree & Architecture Insights */}
              {(treeData || explainer) && (
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

                  {/* Left Column: Interactive Folder Tree (4 cols) */}
                  <div className="lg:col-span-4 space-y-4">
                    <div className="glass-card p-4 rounded-2xl border border-slate-800 bg-[#0e1526]/80 flex flex-col max-h-[680px]">
                      <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
                        <h3 className="text-xs font-bold text-white flex items-center gap-2">
                          <Terminal className="w-4 h-4 text-cyan-400" /> Repository File Tree
                        </h3>
                        <span className="text-[10px] text-slate-400">Click any file to preview</span>
                      </div>
                      <div className="flex-1 overflow-y-auto pr-1">
                        <FolderTree treeString={treeData} onFileClick={handleFileClick} />
                      </div>
                    </div>

                    {/* Important Files Quick Access */}
                    {explainer?.important_files?.length > 0 && (
                      <div className="glass-card p-4 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                        <h3 className="text-xs font-bold text-white mb-2.5 flex items-center gap-2">
                          <CheckSquare className="w-3.5 h-3.5 text-amber-400" /> Key Entry Points
                        </h3>
                        <div className="space-y-1.5">
                          {explainer.important_files.slice(0, 6).map((f, i) => (
                            <div
                              key={i}
                              onClick={() => handleFileClick(f.path)}
                              className="p-2 rounded-lg bg-slate-900/60 hover:bg-slate-800/80 border border-slate-800/80 cursor-pointer transition flex items-center justify-between"
                            >
                              <div className="flex items-center gap-2 truncate">
                                <FileCode className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                                <div className="truncate">
                                  <div className="text-xs font-mono text-cyan-300 truncate">{f.name}</div>
                                  <div className="text-[10px] text-slate-500 truncate">{f.role}</div>
                                </div>
                              </div>
                              <ArrowRight className="w-3 h-3 text-slate-500 shrink-0" />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Right Column: Deep Explanation, Folder Roles, Tech Stack (8 cols) */}
                  <div className="lg:col-span-8 space-y-4">

                    {/* Folder Roles & Why Structure is Used */}
                    {explainer?.folder_roles?.length > 0 && (
                      <div className="glass-card p-5 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                        <h3 className="text-xs font-bold text-white mb-3 flex items-center gap-2">
                          <Layers className="w-4 h-4 text-purple-400" /> Folder Hierarchy & Roles Breakdown
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {explainer.folder_roles.map((r, i) => (
                            <div key={i} className="p-3 rounded-xl bg-slate-900/70 border border-slate-800/80 space-y-1">
                              <div className="flex items-center justify-between">
                                <span className="text-xs font-mono font-bold text-white flex items-center gap-1.5">
                                  <Folder className="w-3.5 h-3.5 text-cyan-400" /> {r.name}/
                                </span>
                                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 font-semibold border border-purple-500/30">
                                  {r.badge}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-400 leading-relaxed">{r.description}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Architecture Analysis Summary */}
                    {explainer?.architecture_summary && (
                      <div className="glass-card p-5 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                        <h3 className="text-xs font-bold text-white mb-2.5 flex items-center gap-2">
                          <Info className="w-4 h-4 text-cyan-400" /> System Architecture & Domain Comprehension
                        </h3>
                        <div className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap max-h-[260px] overflow-y-auto bg-slate-900/50 p-3.5 rounded-xl border border-slate-800/80 font-sans">
                          {explainer.architecture_summary}
                        </div>
                      </div>
                    )}

                    {/* Detected Potential Issues & Health */}
                    {explainer?.detected_issues?.length > 0 && (
                      <div className="glass-card p-4 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                        <h3 className="text-xs font-bold text-white mb-2.5 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-400" /> Digital Twin Codebase Insights ({explainer.detected_issues.length})
                        </h3>
                        <div className="space-y-2">
                          {explainer.detected_issues.map((iss, i) => (
                            <div key={i} className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-start gap-2.5">
                              <AlertCircle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                              <div>
                                <h4 className="text-xs font-semibold text-amber-300">{iss.title}</h4>
                                <p className="text-[11px] text-slate-400 mt-0.5">{iss.description}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Tech Stack & How to Run */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {explainer?.tech_stack && (
                        <div className="glass-card p-4 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                          <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Detected Tech Stack</h4>
                          <div className="flex flex-wrap gap-1.5">
                            {explainer.tech_stack.map((t, i) => (
                              <span key={i} className="px-2.5 py-1 bg-purple-500/15 text-purple-300 border border-purple-500/25 rounded-lg text-xs font-medium">
                                {t}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {explainer?.how_to_run && (
                        <div className="glass-card p-4 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                          <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">How To Run & Test</h4>
                          <div className="space-y-1">
                            {explainer.how_to_run.map((cmd, i) => (
                              <code key={i} className="block text-[11px] text-emerald-400 bg-slate-900/90 px-3 py-1.5 rounded-lg font-mono border border-slate-800/80">
                                {cmd}
                              </code>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                  </div>
                </div>
              )}

              {/* Code Preview Modal */}
              {viewingFile && (
                <div
                  className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-6"
                  onClick={() => setViewingFile(null)}
                >
                  <div
                    className="glass-panel w-full max-w-5xl max-h-[85vh] rounded-2xl border border-slate-700 bg-[#0c1222] flex flex-col shadow-2xl overflow-hidden"
                    onClick={e => e.stopPropagation()}
                  >
                    <div className="px-5 py-3.5 border-b border-slate-800 flex justify-between items-center bg-slate-900/80">
                      <div className="flex items-center gap-2">
                        <FileCode className="w-4 h-4 text-cyan-400" />
                        <span className="font-mono text-xs text-cyan-300 font-bold">{viewingFile.path}</span>
                      </div>
                      <button
                        onClick={() => setViewingFile(null)}
                        className="text-slate-400 hover:text-white px-2 py-1 rounded text-sm font-bold"
                      >
                        ✕
                      </button>
                    </div>
                    <pre className="flex-1 overflow-auto p-5 bg-[#070b14] text-xs font-mono text-slate-200 leading-relaxed">
                      <code>{viewingFile.content}</code>
                    </pre>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 2: 7-AGENT SDLC PIPELINE */}
          {/* ========================================================================= */}
          {activeTab === 'pipeline' && (
            <div className="max-w-4xl mx-auto space-y-6 animate-in fade-in duration-300">

              {/* Task Input Box */}
              <div className="glass-card p-5 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                <div className="flex items-center justify-between mb-2.5">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <Play className="w-4 h-4 text-purple-400" /> Autonomous SDLC Task Input
                  </h2>
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-1.5 text-[11px] text-slate-400 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={useStreaming}
                        onChange={e => setUseStreaming(e.target.checked)}
                        className="w-3 h-3 accent-cyan-500"
                      />
                      Real-time streaming
                    </label>
                    <span className="text-[11px] text-slate-400">Describe any feature, endpoint, bug fix, or new page</span>
                  </div>
                </div>
                <textarea
                  value={taskPrompt}
                  onChange={e => setTaskPrompt(e.target.value)}
                  placeholder="Example: 'Add a /health status endpoint and write unit tests', 'Create category.html in frontend', 'Add user login API with JWT token verification'..."
                  className="w-full bg-slate-900/90 border border-slate-700/80 rounded-xl p-4 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-purple-400 transition min-h-[90px] resize-y font-sans"
                />
                <div className="mt-3 flex items-center justify-between">
                  <div className="text-[11px] text-slate-500">
                    Target Repo: <span className="font-mono text-cyan-400">{repoPath || 'None (Scan repo first)'}</span>
                  </div>
                  <button
                    onClick={handleRunPipeline}
                    disabled={isRunning || !repoPath}
                    className="px-6 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-semibold rounded-xl disabled:opacity-50 transition shadow-lg shadow-purple-600/25 flex items-center gap-2 text-xs"
                  >
                    {isRunning ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
                    {isRunning ? 'Orchestrating 7 Agents...' : 'Execute 7-Agent SDLC'}
                  </button>
                </div>
              </div>

              {/* Agent Timeline Execution */}
              {activeAgentIdx >= 0 && (
                <div className="glass-card p-6 rounded-2xl border border-slate-800 bg-[#0e1526]/80 space-y-4">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-cyan-400" /> Multi-Agent Collaboration Graph
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      {isRunning ? 'Agents actively collaborating & verifying...' : 'Pipeline execution finished'}
                    </span>
                  </div>

                  <div className="space-y-3.5">
                    {AGENTS.map((agent, idx) => {
                      const isPast = activeAgentIdx > idx || completedAgents.has(agent.key);
                      const isCurrent = (activeAgentIdx === idx && isRunning) || (currentAgent === agent.key && isRunning);
                      const isWaiting = !isPast && !isCurrent;
                      const matchingLogs = agentLogs.filter(l => l.agent === agent.key);

                      let containerBg = 'border-slate-800/80 bg-slate-900/40 text-slate-400';
                      if (isPast) containerBg = 'border-slate-700/80 bg-slate-900/80 text-slate-200';
                      if (isCurrent) containerBg = 'border-purple-500/60 bg-purple-950/20 text-white shadow-[0_0_15px_rgba(168,85,247,0.15)]';

                      return (
                        <div key={agent.key} className={`flex items-start gap-3 transition-all duration-300 ${isCurrent ? 'scale-[1.01]' : ''}`}>
                          <div className={`w-8 h-8 rounded-xl flex items-center justify-center border shrink-0 mt-1 transition-all ${
                            isPast ? 'border-cyan-400 bg-cyan-400/10 text-cyan-400' :
                            isCurrent ? 'border-purple-400 bg-purple-400/20 text-purple-300 animate-pulse' :
                            'border-slate-800 bg-slate-900 text-slate-600'
                          }`}>
                            {isPast ? <Check className="w-4 h-4" /> : <agent.icon className="w-4 h-4" />}
                          </div>

                          <div className={`flex-1 border rounded-xl p-3.5 ${containerBg}`}>
                            <div className="flex items-center justify-between mb-1">
                              <div>
                                <h4 className="text-xs font-bold text-white">{agent.name}</h4>
                                <p className="text-[10px] text-slate-500">{agent.desc}</p>
                              </div>
                              {isCurrent && (
                                <span className="text-[10px] text-purple-400 font-semibold uppercase tracking-wider flex items-center gap-1.5">
                                  <Activity className="w-3 h-3 animate-spin" /> RUNNING
                                </span>
                              )}
                              {isPast && <span className="text-[10px] text-cyan-400 font-semibold uppercase tracking-wider">COMPLETE</span>}
                              {isWaiting && <span className="text-[10px] text-slate-600 font-semibold uppercase tracking-wider">WAITING</span>}
                            </div>

                            {/* Agent Action Log */}
                            {matchingLogs.map((log, i) => (
                              <div key={i} className="mt-2.5 pt-2 border-t border-slate-800/80">
                                <div className="text-[11px] font-semibold text-cyan-300 mb-1">{log.action}</div>
                                <pre className="text-[11px] text-slate-400 font-mono bg-slate-950/80 p-2.5 rounded-lg max-h-[140px] overflow-y-auto whitespace-pre-wrap border border-slate-800/50">
                                  {log.output?.substring(0, 1000)}{log.output?.length > 1000 ? '...' : ''}
                                </pre>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Completion Banner */}
                  {pipelineResult && generatedFiles.length > 0 && (
                    <div className="mt-5 p-4 rounded-xl bg-gradient-to-r from-emerald-500/15 via-teal-500/10 to-cyan-500/15 border border-emerald-500/30 flex items-center justify-between animate-in fade-in">
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                        <div>
                          <h4 className="text-xs font-bold text-emerald-300">SDLC Pipeline Successfully Executed!</h4>
                          <p className="text-[11px] text-slate-400 mt-0.5">
                            {generatedFiles.length} file(s) generated & verified against architectural boundaries.
                          </p>
                        </div>
                      </div>
                      <button
                        onClick={() => setActiveTab('review')}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold rounded-xl text-xs flex items-center gap-2 transition shadow-lg shadow-emerald-600/20"
                      >
                        <Eye className="w-3.5 h-3.5" /> Review & Deploy Code
                      </button>
                    </div>
                  )}

                </div>
              )}

            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 3: CODE REVIEW & DEPLOY */}
          {/* ========================================================================= */}
          {activeTab === 'review' && (
            <div className="max-w-7xl mx-auto h-[calc(100vh-140px)] flex flex-col gap-4 animate-in fade-in duration-300">

              {/* Review Actions Header */}
              <div className="glass-card p-4 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                <div className="flex items-center justify-between flex-wrap gap-3">
                  <div>
                    <h2 className="text-sm font-bold text-white flex items-center gap-2">
                      <FileCode className="w-4 h-4 text-cyan-400" /> Review Generated Code & Deploy
                    </h2>
                    <p className="text-[11px] text-slate-400">
                      Verify generated files, merge locally, commit, push, or open Pull Request on GitHub
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    {/* Step 1: Merge to Disk */}
                    {mergeSuccess ? (
                      <span className="px-3 py-2 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded-xl text-xs font-semibold flex items-center gap-1.5">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Merged to Disk
                      </span>
                    ) : (
                      <button
                        onClick={handleMerge}
                        disabled={isMerging || !generatedFiles.length}
                        className="px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 text-white font-semibold rounded-xl text-xs disabled:opacity-50 transition shadow-lg shadow-emerald-600/20 flex items-center gap-1.5"
                      >
                        {isMerging ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <Merge className="w-3.5 h-3.5" />}
                        Merge to Disk
                      </button>
                    )}

                    {/* Step 2: Local Commit */}
                    <button
                      onClick={handleGitCommit}
                      disabled={isCommitting || !repoPath}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-purple-300 font-semibold rounded-xl text-xs border border-purple-500/30 transition flex items-center gap-1.5"
                    >
                      {isCommitting ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <GitCommit className="w-3.5 h-3.5" />}
                      Commit
                    </button>

                    {/* Step 3: Push to Remote */}
                    <button
                      onClick={handleGitPush}
                      disabled={isPushing || !repoPath}
                      className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-amber-300 font-semibold rounded-xl text-xs border border-amber-500/30 transition flex items-center gap-1.5"
                      title="Push current branch to remote"
                    >
                      {isPushing ? <Activity className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                      Push
                    </button>

                    {/* Step 4: Open Pull Request */}
                    <button
                      onClick={handleOpenPRModal}
                      disabled={!repoPath}
                      className="px-4 py-2 bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-semibold rounded-xl text-xs transition shadow-lg shadow-cyan-600/20 flex items-center gap-1.5"
                    >
                      <GitPullRequest className="w-3.5 h-3.5" />
                      Open Pull Request
                    </button>
                  </div>
                </div>

                {/* Status Badges */}
                <div className="flex items-center gap-2 mt-2.5 flex-wrap">
                  {commitResult?.committed && (
                    <span className="text-[10px] px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded-lg border border-purple-500/30 font-mono">
                      Commit: {commitResult.commit_hash}
                    </span>
                  )}
                  {pushResult?.status === 'success' && (
                    <span className="text-[10px] px-2 py-0.5 bg-amber-500/20 text-amber-300 rounded-lg border border-amber-500/30 font-mono">
                      Pushed: {pushResult.branch}
                    </span>
                  )}
                  {prResult?.status === 'success' && (
                    <a
                      href={prResult.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[10px] px-2.5 py-0.5 bg-cyan-500/20 text-cyan-300 rounded-lg border border-cyan-500/30 flex items-center gap-1 hover:bg-cyan-500/30 transition font-semibold"
                    >
                      <GitPullRequest className="w-3 h-3 text-cyan-400" />
                      PR #{prResult.pr_number} Created (View on GitHub) <ExternalLink className="w-2.5 h-2.5" />
                    </a>
                  )}
                </div>
              </div>

              {/* One-Click Deploy Section */}
              {generatedFiles.length > 0 && !mergeSuccess && (
                <div className="glass-card p-4 rounded-2xl border border-indigo-500/30 bg-indigo-950/20 space-y-3">
                  <div className="flex items-center justify-between flex-wrap gap-3">
                    <div className="flex items-center gap-3">
                      <Rocket className="w-5 h-5 text-indigo-400 shrink-0" />
                      <div>
                        <h3 className="text-xs font-bold text-indigo-300">1-Click Autonomous Deploy Pipeline</h3>
                        <p className="text-[10px] text-slate-400">
                          {deployPR ? 'Team Lead Review: Feature Branch → Merge → Commit → Push → Open PR on GitHub' : 'Direct Contributor: Merge → Commit → Push to Active Branch → CI/CD Actions Run'}
                        </p>
                      </div>
                    </div>

                    {/* Mode Selector */}
                    <div className="flex items-center gap-1.5 p-1 bg-slate-900/90 rounded-xl border border-slate-800 text-[11px]">
                      <button
                        onClick={() => {
                          setDeployMode('pr');
                          setDeployBranch(true);
                          setDeployPush(true);
                          setDeployPR(true);
                        }}
                        className={`px-3 py-1 rounded-lg font-semibold transition ${
                          deployMode === 'pr'
                            ? 'bg-gradient-to-r from-cyan-600 to-indigo-600 text-white shadow'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Team Lead PR Mode
                      </button>
                      <button
                        onClick={() => {
                          setDeployMode('direct');
                          setDeployBranch(false);
                          setDeployPush(true);
                          setDeployPR(false);
                        }}
                        className={`px-3 py-1 rounded-lg font-semibold transition ${
                          deployMode === 'direct'
                            ? 'bg-gradient-to-r from-emerald-600 to-teal-600 text-white shadow'
                            : 'text-slate-400 hover:text-slate-200'
                        }`}
                      >
                        Direct Deploy Mode
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between flex-wrap gap-3 pt-2 border-t border-indigo-500/20">
                    <div className="flex items-center gap-4 flex-wrap">
                      <label className="flex items-center gap-1.5 text-[10px] text-slate-400 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={deployBranch}
                          onChange={e => setDeployBranch(e.target.checked)}
                          className="w-3 h-3 accent-indigo-500"
                        />
                        Feature Branch
                      </label>
                      <label className="flex items-center gap-1.5 text-[10px] text-slate-400 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={deployPush}
                          onChange={e => setDeployPush(e.target.checked)}
                          className="w-3 h-3 accent-amber-500"
                        />
                        Push to Remote
                      </label>
                      <label className="flex items-center gap-1.5 text-[10px] text-slate-400 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={deployPR}
                          onChange={e => setDeployPR(e.target.checked)}
                          className="w-3 h-3 accent-cyan-500"
                          disabled={!deployPush}
                        />
                        Open GitHub PR
                      </label>
                    </div>

                    <button
                      onClick={handleDeploy}
                      disabled={isDeploying}
                      className="px-6 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-semibold rounded-xl text-xs disabled:opacity-50 transition shadow-lg shadow-indigo-600/20 flex items-center gap-2"
                    >
                      {isDeploying ? <Activity className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                      {isDeploying ? 'Executing Pipeline...' : deployPR ? 'Deploy & Open PR' : 'Deploy & Push Now'}
                    </button>
                  </div>

                  {/* Deploy Result Steps */}
                  {deployResult?.steps && (
                    <div className="mt-3 flex items-center gap-2 flex-wrap">
                      {deployResult.steps.map((step, i) => (
                        <span
                          key={i}
                          className={`text-[10px] px-2 py-0.5 rounded-lg border flex items-center gap-1 ${
                            step.status === 'success'
                              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                              : step.status === 'skipped'
                              ? 'bg-slate-500/20 text-slate-300 border-slate-500/30'
                              : 'bg-red-500/20 text-red-300 border-red-500/30'
                          }`}
                        >
                          {step.status === 'success' ? <Check className="w-2.5 h-2.5" /> : step.status === 'skipped' ? '–' : <AlertCircle className="w-2.5 h-2.5" />}
                          {step.step}: {step.message?.slice(0, 40) || step.status}
                          {step.pr_url && (
                            <a href={step.pr_url} target="_blank" rel="noopener noreferrer" className="underline ml-1">
                              View PR
                            </a>
                          )}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {!generatedFiles.length ? (
                <div className="flex-1 glass-card rounded-2xl border border-slate-800 bg-[#0e1526]/40 flex flex-col items-center justify-center text-slate-500">
                  <Code2 className="w-16 h-16 mb-3 opacity-20" />
                  <p className="text-xs font-medium">No generated files to review. Execute the 7-Agent SDLC pipeline first.</p>
                  <button
                    onClick={() => setActiveTab('pipeline')}
                    className="mt-3 px-4 py-2 bg-purple-600/30 text-purple-300 border border-purple-500/30 rounded-xl text-xs hover:bg-purple-600/40 transition"
                  >
                    Go to SDLC Pipeline
                  </button>
                </div>
              ) : (
                <div className="flex-1 flex gap-4 min-h-0">
                  {/* Left Column: List of Generated Files */}
                  <div className="w-72 glass-card rounded-2xl border border-slate-800 bg-[#0e1526]/80 p-3 flex flex-col overflow-hidden shrink-0">
                    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2.5 px-2">
                      Generated Code ({generatedFiles.length})
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-1">
                      {generatedFiles.map(f => {
                        const isNew = !originalCode[f];
                        const isSelected = selectedFile === f;
                        const isCICD = f.includes('.github') || f.includes('Dockerfile') || f.includes('docker-compose');
                        return (
                          <button
                            key={f}
                            onClick={() => setSelectedFile(f)}
                            className={`w-full text-left px-3 py-2.5 rounded-xl text-xs font-mono transition flex items-center justify-between ${
                              isSelected
                                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
                                : 'text-slate-300 hover:bg-slate-800/60 border border-transparent'
                            }`}
                          >
                            <span className="truncate mr-2">{f}</span>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                              isCICD ? 'bg-orange-500/20 text-orange-300' :
                              isNew ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
                            }`}>
                              {isCICD ? 'CI/CD' : isNew ? 'NEW' : 'MOD'}
                            </span>
                          </button>
                        );
                      })}
                    </div>

                    <div className="pt-2.5 border-t border-slate-800 mt-2 px-2 flex items-center justify-between text-[10px] text-slate-500 flex-wrap gap-1">
                      <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400" /> New</span>
                      <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400" /> Modified</span>
                      <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-orange-400" /> CI/CD</span>
                    </div>
                  </div>

                  {/* Right Column: Code Diff / Viewer */}
                  <div className="flex-1 glass-card rounded-2xl border border-slate-800 bg-[#0c1222] flex flex-col overflow-hidden min-h-0">
                    <div className="bg-slate-900/90 px-4 py-2.5 border-b border-slate-800 flex items-center justify-between">
                      <div className="flex items-center gap-2 text-xs font-mono text-cyan-300 font-bold">
                        <Terminal className="w-3.5 h-3.5" />
                        <span>{selectedFile || 'Select a file'}</span>
                      </div>
                      {selectedFile && (
                        <button
                          onClick={() => {
                            navigator.clipboard.writeText(generatedCode[selectedFile]);
                            showToast('Code copied to clipboard!');
                          }}
                          className="text-[11px] text-slate-400 hover:text-white flex items-center gap-1 bg-slate-800 px-2.5 py-1 rounded-lg"
                        >
                          <Copy className="w-3 h-3" /> Copy
                        </button>
                      )}
                    </div>
                    <div className="flex-1 overflow-auto p-4 bg-[#070b14]">
                      {selectedFile && generatedCode[selectedFile] ? (
                        <pre className="text-xs font-mono text-slate-200 leading-relaxed whitespace-pre-wrap">
                          <code>{generatedCode[selectedFile]}</code>
                        </pre>
                      ) : (
                        <div className="h-full flex items-center justify-center text-xs text-slate-600">
                          Select a generated file from the left to view code
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

            </div>
          )}

          {/* ========================================================================= */}
          {/* TAB 4: SEMANTIC SEARCH */}
          {/* ========================================================================= */}
          {activeTab === 'search' && (
            <div className="max-w-5xl mx-auto space-y-6 animate-in fade-in duration-300">

              <div className="glass-card p-5 rounded-2xl border border-slate-800 bg-[#0e1526]/80">
                <h2 className="text-sm font-bold text-white mb-1 flex items-center gap-2">
                  <Search className="w-4 h-4 text-cyan-400" /> ChromaDB Semantic Codebase Search
                </h2>
                <p className="text-[11px] text-slate-400 mb-3.5">
                  Vector search across your codebase index to find functions, endpoints, database schemas, and logic
                </p>
                <div className="flex gap-3">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && handleSearch()}
                    placeholder="Search for concepts, e.g. 'JWT authentication', 'health route', 'database models'..."
                    className="flex-1 bg-slate-900/90 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 transition"
                  />
                  <button
                    onClick={handleSearch}
                    disabled={isSearching || !searchQuery.trim()}
                    className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-white font-semibold rounded-xl transition text-xs flex items-center gap-2 border border-slate-700"
                  >
                    {isSearching ? <Activity className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    Search Index
                  </button>
                </div>
              </div>

              {searchResults.length > 0 && (
                <div className="space-y-3">
                  {searchResults.map((res, i) => (
                    <div
                      key={i}
                      onClick={() => handleFileClick(res.path)}
                      className="glass-card p-4 rounded-xl border border-slate-800 hover:border-cyan-500/40 bg-[#0e1526]/60 cursor-pointer transition"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-mono font-bold text-cyan-400 flex items-center gap-2">
                          <FileCode className="w-4 h-4" /> {res.path}
                        </span>
                        {res.score !== undefined && (
                          <span className="text-[10px] bg-slate-800 px-2 py-0.5 rounded text-slate-400 font-mono">
                            Dist: {res.score.toFixed(3)}
                          </span>
                        )}
                      </div>
                      <pre className="text-xs text-slate-300 font-mono bg-slate-950/80 p-3 rounded-lg max-h-[120px] overflow-hidden border border-slate-800/60">
                        {res.content?.substring(0, 600)}
                      </pre>
                    </div>
                  ))}
                </div>
              )}

            </div>
          )}

        </div>
      </main>

    </div>
  );
}
