import streamlit as st
import sys, os, json, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from agent import CareerAgent
from tools import sanitize_output, safe_text_output, sanitize_interview_questions
from growth_share_compare import load as _gh_load, append as _gh_append, trend as _gh_trend

try:
    import plotly.graph_objects as go
    _HAS_PLOTLY = True
except ImportError:
    _HAS_PLOTLY = False
import math
def _radar_chart(scores):
    if not _HAS_PLOTLY or scores is None: return None
    labels = [chr(25216)+chr(33021)+chr(21305)+chr(37197), chr(32463)+chr(39564)+chr(31561)+chr(32423), chr(39033)+chr(30446)+chr(36136)+chr(37327), chr(65)+chr(73)+chr(30456)+chr(20851)+chr(24230), chr(32508)+chr(21512)]
    keys = ['research','practice','analysis','communication','overall']
    vals = [scores.get(k, 0) for k in keys]
    vals.append(vals[0]); labels.append(labels[0])
    fig = go.Figure(data=go.Scatterpolar(r=vals, theta=labels, fill='toself', line_color='#3B82F6'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0,100]), domain=dict(x=[0,1], y=[0,1])), showlegend=False, height=200, margin=dict(l=30,r=30,t=30,b=30), paper_bgcolor='white', plot_bgcolor='rgba(0,0,0,0)')
    return fig


st.set_page_config(page_title='AI Career Agent', page_icon='💼', layout='wide', initial_sidebar_state='expanded')

st.markdown('''<style>
    .stApp { background: #f7f8fc; }
    .block-container { padding-top: 1rem !important; max-width: 1440px !important; }
    .app-header { background: linear-gradient(135deg, #EEF2FF, #F5F3FF, #ECFDF5); border-radius: 20px; padding: 24px 32px; margin-bottom: 24px; text-align: center; border: 1px solid rgba(255,255,255,0.6); }
    .app-title { font-size: 26px; font-weight: 700; color: #111827; }
    .app-sub { font-size: 14px; color: #6B7280; margin-top: 4px; }
    .card { background: #fff; border-radius: 16px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); border: 1px solid #F3F4F6; margin-bottom: 14px; }
    .card-label { font-size: 11px; font-weight: 600; color: #9CA3AF; letter-spacing: 0.3px; margin-bottom: 8px; }
    .stTextArea textarea { border-radius: 12px !important; border: 1px solid #E5E7EB !important; font-size: 14px !important; padding: 12px 14px !important; background: #F9FAFB !important; }
    div.stButton > button:first-child { background: #3B82F6 !important; color: #fff !important; border: none !important; border-radius: 12px !important; padding: 10px 24px !important; font-weight: 600 !important; }
    .stProgress > div > div > div > div { background: linear-gradient(90deg,#3B82F6,#60A5FA) !important; }
    [data-testid="stMetricValue"] { font-size: 44px !important; font-weight: 800 !important; color: #111827 !important; }
    .skill-pill { display: inline-block; padding: 4px 14px; border-radius: 20px; font-size: 12px; font-weight: 500; margin: 3px 5px; }
    .skill-green { background: #ECFDF5; color: #065F46; border: 1px solid #D1FAE5; }
    .skill-red { background: #FEF2F2; color: #991B1B; border: 1px solid #FECACA; }
    .mode-badge { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11px; font-weight: 600; }
    .mode-rag { background: #EFF6FF; color: #3B82F6; }
    .mode-llm { background: #F3F4F6; color: #6B7280; }
    .q-item { padding: 4px 0; font-size: 14px; color: #374151; }
    footer { visibility: hidden; }
</style>''', unsafe_allow_html=True)

st.markdown('<div class="app-header"><div class="app-title">💼 AI Career Agent</div><div class="app-sub">智能求职分析 · 多维度评分 · RAG+规则双引擎</div></div>', unsafe_allow_html=True)

for k in ['result','done','api_key']:
    if k not in st.session_state:
        s = st.secrets.get("DEEPSEEK_API_KEY", "") if k=='api_key' else ''
        st.session_state[k] = None if k=='result' else False if k=='done' else s

with st.sidebar:
    st.markdown('### 🔑 配置')
    ak = st.text_input('DeepSeek API Key', type='password', placeholder='sk-xxxxxxxxxxxxxxxx', value=st.session_state.get('api_key','') or st.secrets.get("DEEPSEEK_API_KEY", ""), key='api_key_input')
    st.session_state.api_key = ak
    if ak:
        os.environ['DEEPSEEK_API_KEY'] = ak
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown(':bulb: **使用说明**')
    st.markdown('1. 输入简历')
    st.markdown('2. 输入职位描述')
    st.markdown('3. 点击开始分析')
    st.markdown('4. 查看多维度报告')

col_left, col_mid, col_right = st.columns([1.5, 2.5, 1.8], gap='medium')

def render_interview_probability(result, resume="", jd=""):
    st.subheader(chr(127919)+chr(32)+chr(38754)+chr(35797)+chr(36890)+chr(36807)+chr(29575)+chr(39044)+chr(27979))
    scores = result.get("scores", {})
    overall = scores.get("overall", 0)
    prob = min(95, max(30, int(overall * 0.7 + scores.get("skill_match", 0) * 0.2 + scores.get("experience", 0) * 0.1)))
    if prob >= 80:
        st.success(chr(128994)+chr(32)+chr(39640)+chr(27010)+chr(29575)+chr(36890)+chr(36807)+chr(38754)+chr(35797)+chr(65306)+str(prob)+chr(37))
    elif prob >= 60:
        st.warning(chr(128993)+chr(32)+chr(20013)+chr(31561)+chr(27010)+chr(29575)+chr(36890)+chr(36807)+chr(65306)+str(prob)+chr(37))
    else:
        st.error(chr(128308)+chr(32)+chr(36890)+chr(36807)+chr(29575)+chr(36739)+chr(20302)+chr(65306)+str(prob)+chr(37))
    st.markdown(chr(35)+chr(35)+chr(35)+chr(32)+chr(128202)+chr(32)+chr(24433)+chr(21709)+chr(22240)+chr(32032))
    st.write(chr(25216)+chr(33021)+chr(21305)+chr(37197)+chr(65306)+str(scores.get("skill_match", 0)))
    st.write(chr(32463)+chr(39564)+chr(21305)+chr(37197)+chr(65306)+str(scores.get("experience", 0)))
    st.write(chr(39033)+chr(30446)+chr(33021)+chr(21147)+chr(65306)+str(scores.get("project", 0)))
    st.write(chr(65)+chr(73)+chr(30456)+chr(20851)+chr(24615)+chr(65306)+str(scores.get("ai_relevance", 0)))
    st.markdown(chr(35)+chr(35)+chr(35)+chr(32)+chr(9888)+chr(65039)+chr(32)+chr(24314)+chr(35758)+chr(20248)+chr(21270)+chr(28857))
    _sugs = result.get("optimization_suggestions")
    if not _sugs and st.session_state.get("api_key"):
        try:
            _ag = CareerAgent(api_key=st.session_state.api_key)
            _sugs = _ag.generate_suggestions(result, resume, jd)
            if _sugs:
                result["optimization_suggestions"] = _sugs
        except:
            pass
    if _sugs:
        for _s in _sugs:
            st.write(chr(8226)+chr(32)+str(_s))
    else:
        _miss = result.get("skills_missing", [])
        if _miss:
            for _s2 in _miss[:3]:
                st.write(chr(8226)+chr(32)+chr(24314)+chr(35758)+chr(34917)+chr(20805)+chr(32)+str(_s2)+chr(32)+chr(30456)+chr(20851)+chr(32463)+chr(39564))
        elif prob < 80:
            st.write(chr(8226)+chr(32)+chr(24314)+chr(35758)+chr(34917)+chr(20805)+chr(39033)+chr(30446)+chr(32463)+chr(39564))
            st.write(chr(8226)+chr(32)+chr(21152)+chr(24378)+chr(39640)+chr(39039)+chr(38754)+chr(35797)+chr(39064)+chr(20934)+chr(22791)+chr(65288)+chr(83)+chr(81)+chr(76)+chr(32)+chr(47)+chr(32)+chr(31995)+chr(32479)+chr(35774)+chr(35745)+chr(65289))
        else:
            st.write(chr(8226)+chr(32)+chr(21487)+chr(20197)+chr(30452)+chr(25509)+chr(25237)+chr(36882)+chr(65292)+chr(24182)+chr(20934)+chr(22791)+chr(38754)+chr(35797)+chr(28145)+chr(25496))

with col_left:
    st.markdown('<div class="card"><div class="card-label">📝 输入信息</div>', unsafe_allow_html=True)
    resume = st.text_area('resume', height=150, placeholder='粘贴简历（教育、工作、技能、项目）', label_visibility='collapsed')
    st.markdown('<div style="height:6px;"></div>', unsafe_allow_html=True)
    jd = st.text_area('jd', height=150, placeholder='粘贴职位描述（要求、技能、职责）', label_visibility='collapsed')
    st.markdown('<div style="height:10px;"></div>', unsafe_allow_html=True)
    can_run = bool(resume and jd)
    clicked = st.button(':🚀 开始分析', use_container_width=True, disabled=not can_run)
    st.markdown('</div>', unsafe_allow_html=True)
    if not can_run:
        st.markdown('<div style="text-align:center;padding:10px;color:#9CA3AF;font-size:13px;border:1px dashed #E5E7EB;border-radius:12px;">💡 请输入简历和JD</div>', unsafe_allow_html=True)

    if st.session_state.done and st.session_state.result:
        render_interview_probability(st.session_state.result, resume, jd)

with col_mid:
    st.markdown('<div style="font-size:14px;font-weight:600;color:#111827;margin-bottom:12px;">📊 分析报告</div>', unsafe_allow_html=True)

    if clicked and resume and jd:
        if not st.session_state.api_key:
            st.error('🔑 请配置 API Key')
        else:
            with st.spinner('AI 分析中...'):
                try:
                    agent = CareerAgent(api_key=st.session_state.api_key)
                    result = agent.run(resume, jd)
                    st.session_state.result = result
                    st.session_state.done = True
                    _gh_append(result.get('scores',{}).get('overall',0))
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    if st.session_state.done and st.session_state.result:
        d = st.session_state.result
        if d is None: d = {}
        scores = d.get('scores', {})
        overall = scores.get('overall', 0)
        sc_c = '#10B981' if overall >= 80 else '#3B82F6' if overall >= 60 else '#EF4444'

        st.markdown(f'<div class="card"><div class="card-label">🎯 综合匹配度</div><div style="font-size:48px;font-weight:800;letter-spacing:-2px;color:{sc_c};">{overall}%</div></div>', unsafe_allow_html=True)
        st.progress(overall / 100.0)
        fig = _radar_chart(scores)
        if fig:
            st.markdown(chr(60)+chr(100)+chr(105)+chr(118)+chr(32)+chr(99)+chr(108)+chr(97)+chr(115)+chr(115)+chr(61)+chr(34)+chr(99)+chr(97)+chr(114)+chr(100)+chr(34)+chr(62)+chr(60)+chr(100)+chr(105)+chr(118)+chr(32)+chr(99)+chr(108)+chr(97)+chr(115)+chr(115)+chr(61)+chr(34)+chr(99)+chr(97)+chr(114)+chr(100)+chr(45)+chr(108)+chr(97)+chr(98)+chr(101)+chr(108)+chr(34)+chr(62)+chr(128200)+chr(32)+chr(33021)+chr(21147)+chr(38647)+chr(36798)+chr(22270)+chr(60)+chr(47)+chr(100)+chr(105)+chr(118)+chr(62)+chr(60)+chr(47)+chr(100)+chr(105)+chr(118)+chr(62), unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True)

        dims = [('研究能力','research'),('实践能力','practice'),('分析能力','analysis'),('沟通能力','communication')]
        st.markdown('<div class="card"><div class="card-label">📊 多维度评分</div>', unsafe_allow_html=True)
        for label, key in dims:
            val = scores.get(key, 0)
            st.markdown(f'<div style="display:flex;justify-content:space-between;font-size:13px;color:#6B7280;margin-bottom:2px;"><span>{label}</span><span style="font-weight:600;color:#111827;">{val}%</span></div>', unsafe_allow_html=True)
            st.progress(val / 100.0)
        st.markdown('</div>', unsafe_allow_html=True)

        analysis = d.get('analysis', '')
        if isinstance(analysis, str) and analysis.strip():
            safe_a = sanitize_output(analysis)
            st.markdown(f'<div class="card"><div class="card-label">📄 详细分析</div><div style="font-size:14px;color:#374151;line-height:1.7;">{safe_a}</div></div>', unsafe_allow_html=True)

        expl = d.get('score_explanation', '')
        if isinstance(expl, str) and expl.strip():
            safe_e = sanitize_output(expl)
            st.markdown(f'<div class="card"><div class="card-label">💡 评分说明</div><div style="font-size:14px;color:#374151;line-height:1.7;">{safe_e}</div></div>', unsafe_allow_html=True)

        iq = sanitize_interview_questions(d.get('interview_questions', {}))
        if isinstance(iq, dict):
            tech = iq.get('technical', []); beh = iq.get('behavioral', []); proj = iq.get('project', [])
            if any(isinstance(x,list) and len(x)>0 for x in [tech, beh, proj]):
                with st.expander('🎤 面试问题', expanded=False):
                    if isinstance(tech,list) and tech:
                        st.markdown("**技术问题**")
                        for q in tech:
                            st.markdown(f'<div class="q-item">• {safe_text_output(q)}</div>', unsafe_allow_html=True)
                    if isinstance(beh,list) and beh:
                        st.markdown("**行为问题**")
                        for q in beh:
                            st.markdown(f'<div class="q-item">• {safe_text_output(q)}</div>', unsafe_allow_html=True)
                    if isinstance(proj,list) and proj:
                        st.markdown("**项目问题**")
                        for q in proj:
                            st.markdown(f'<div class="q-item">• {safe_text_output(q)}</div>', unsafe_allow_html=True)

        _ro_opt = d.get('resume_optimization',{}).get('optimized','')
        if isinstance(_ro_opt, str) and len(_ro_opt) > 10:
            with st.expander('📄 简历对比优化', expanded=False):
                c_a, c_b = st.columns(2)
                with c_a: st.markdown('**原始简历**'); st.markdown(f'<div style="font-size:13px;color:#6B7280;line-height:1.6;">{resume[:500]}</div>', unsafe_allow_html=True)
                with c_b: st.markdown('**优化简历**'); st.markdown(f'<div style="font-size:13px;color:#10B981;line-height:1.6;">{_ro_opt[:500]}</div>', unsafe_allow_html=True)

    else:
        st.markdown('<div class="card" style="text-align:center;padding:60px 20px;"><div style="font-size:36px;opacity:0.2;margin-bottom:10px;">💼</div><div style="font-size:15px;font-weight:500;color:#6B7280;">等待分析</div><div style="font-size:13px;color:#9CA3AF;margin-top:4px;">请在左侧输入简历和职位描述</div></div>', unsafe_allow_html=True)

with col_right:
    st.markdown('<div style="font-size:14px;font-weight:600;color:#111827;margin-bottom:12px;">📇 摘要</div>', unsafe_allow_html=True)

    if st.session_state.done and st.session_state.result:
        d = st.session_state.result
        if d is None: d = {}
        scores = d.get('scores', {})

        dec = str(d.get('decision', 'llm'))
        rec = str(d.get('recommendation', ''))
        conf = float(d.get('confidence', 0.0))
        mc = 'mode-rag' if dec == 'rag' else 'mode-llm'
        dl = 'RAG 知识库' if dec == 'rag' else 'LLM 通用分析'
        st.markdown(f'<div class="card"><div class="card-label">🎯 决策模式</div><span class="mode-badge {mc}">{dl}</span><div style="margin-top:8px;font-size:14px;font-weight:600;color:#111827;">{sanitize_output(rec)}</div><div style="font-size:12px;color:#6B7280;margin-top:2px;">置信度: {conf:.2f}</div></div>', unsafe_allow_html=True)

        matched = d.get('skills_matched', [])
        missing = d.get('skills_missing', [])
        if isinstance(matched, list) and matched:
            tags = ''.join(f'<span class="skill-pill skill-green">{sanitize_output(str(s))}</span>' for s in matched)
            st.markdown(f'<div class="card"><div class="card-label">✅ 已匹配技能</div><div>{tags}</div></div>', unsafe_allow_html=True)
        if isinstance(missing, list) and missing:
            tags = ''.join(f'<span class="skill-pill skill-red">{sanitize_output(str(s))}</span>' for s in missing)
            st.markdown(f'<div class="card"><div class="card-label">🔧 待提升技能</div><div>{tags}</div></div>', unsafe_allow_html=True)

        recs = d.get('career_recommendations', [])
        if isinstance(recs, list) and recs:
            html = '<div class="card"><div class="card-label">🚀 职业推荐</div>'
            for r_item in recs[:3]:
                if isinstance(r_item, dict):
                    role = sanitize_output(str(r_item.get('role','')))
                    reason = sanitize_output(str(r_item.get('reason','')))
                    ml = int(r_item.get('match_level', 0))
                    html += f'<div style="padding:8px 0;border-bottom:1px solid #F3F4F6;"><div style="font-size:14px;font-weight:600;color:#111827;">{role}</div><div style="font-size:12px;color:#6B7280;">{reason}</div><span style="font-size:13px;font-weight:600;color:#3B82F6;">{ml}%</span></div>'
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        _ss = scores.get('overall', 0)
        _sr = d.get('recommendation', '')
        _sm = ', '.join(d.get('skills_matched', [])[:3])
        if st.button('📱 生成分享卡片', use_container_width=True):
            style = 'background:linear-gradient(135deg,#EEF2FF,#F5F3FF);border-radius:16px;padding:20px;text-align:center;font-family:sans-serif;'
            _card = f'''<div style="{style}"><div style="font-size:28px;font-weight:700;color:#111827;margin-bottom:4px;">{_ss}%</div><div style="font-size:14px;color:#6B7280;margin-bottom:12px;">匹配度</div><div style="font-size:15px;font-weight:600;color:#3B82F6;margin-bottom:8px;">{_sr}</div><div style="font-size:13px;color:#374151;margin-bottom:4px;">优势技能: {_sm}</div><div style="font-size:11px;color:#9CA3AF;margin-top:12px;">AI Career Agent</div></div>'''
            st.markdown('### 📱 分享卡片')
            st.markdown(_card, unsafe_allow_html=True)
            _txt = f'AI Career Agent 分析报告\n匹配度: {_ss}%\n建议: {_sr}\n优势技能: {_sm}\n---\n由 AI Career Agent 生成'
            st.code(_txt, language='text')

        sg = d.get('skill_gap', {})
        lp = sg.get('learning_path', []) if isinstance(sg, dict) else []
        if isinstance(lp, list) and lp:
            with st.expander('📚 学习路径', expanded=False):
                for item in lp:
                    st.markdown(f'- {sanitize_output(str(item))}')

    else:
        st.markdown('<div class="card" style="text-align:center;padding:30px 12px;"><div style="font-size:14px;color:#9CA3AF;">等待输入...</div></div>', unsafe_allow_html=True)

st.markdown('<div style="text-align:center;padding:20px 0 8px;color:#D1D5DB;font-size:12px;">AI Career Agent &middot; Powered by DeepSeek</div>', unsafe_allow_html=True)
