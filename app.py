import streamlit as st
import pandas as pd
import json
import io
import datetime

# ==========================================
# 1. 页面配置与主题初始化
# ==========================================
st.set_page_config(layout="wide", page_title="Shein 成人用品标注工具")

# 初始化 session_state 用于存储数据和文件信息
if 'data' not in st.session_state:
    st.session_state.data = []
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'original_filename' not in st.session_state:
    st.session_state.original_filename = "data"

# ==========================================
# 2. 核心功能函数
# ==========================================
def load_data(uploaded_file):
    """读取上传的JSONL文件并存入session_state"""
    if uploaded_file is not None:
        try:
            # 记录原始文件名（去掉扩展名）
            st.session_state.original_filename = uploaded_file.name.rsplit('.', 1)[0]
            
            # 读取文件内容
            stringio = io.StringIO(uploaded_file.getvalue().decode("utf-8"))
            data_list = []
            for line in stringio:
                if line.strip():
                    item = json.loads(line)
                    # 确保每个item都有label字段，如果没有则默认为 'unlabeled'
                    if 'label' not in item or not item['label']:
                        item['label'] = 'unlabeled'
                    data_list.append(item)
            
            st.session_state.data = data_list
            st.session_state.data_loaded = True
        except Exception as e:
            st.error(f"文件读取失败: {e}")

def update_label(index, new_label):
    """更新指定索引数据的标签并触发刷新"""
    st.session_state.data[index]['label'] = new_label
    # Streamlit 会在状态改变后自动重新运行脚本

def convert_to_jsonl(data):
    """将数据转换为JSONL格式字符串"""
    jsonl_str = ""
    for item in data:
        jsonl_str += json.dumps(item, ensure_ascii=False) + "\n"
    return jsonl_str

# ==========================================
# 3. 侧边栏布局 (Sidebar)
# ==========================================
with st.sidebar:
    st.header("📂 数据导入")
    uploaded_file = st.file_uploader("上传待审核的 JSONL 文件", type=['jsonl', 'json'])
    
    if uploaded_file and not st.session_state.data_loaded:
        load_data(uploaded_file)
    
    if st.session_state.data_loaded:
        st.divider()
        st.header("🔍 筛选与控制")
        
        # 1. 标注状态筛选 (Neil 要求的核心功能)
        status_options = ["All", "unlabeled", "pos", "neg", "disable"]
        selected_status = st.selectbox("筛选标注状态", status_options)
        
        # 2. 搜索类型筛选
        all_search_types = list(set([str(item.get('search_type', 'Unknown')) for item in st.session_state.data]))
        selected_search_type = st.multiselect("筛选 Search Type", all_search_types, default=all_search_types)
        
        # 3. 分页设置
        items_per_page = st.slider("每页显示条数", 5, 50, 10)
        
        st.divider()
        st.header("💾 结果导出")
        
        # 生成动态文件名逻辑：原文件名 + 时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"{st.session_state.original_filename}_{timestamp}_labeled_data.jsonl"
        
        jsonl_output = convert_to_jsonl(st.session_state.data)
        st.download_button(
            label="📥 下载标注结果 (JSONL)",
            data=jsonl_output,
            file_name=export_filename,
            mime="application/json",
            help="导出包含当前所有标注状态的全量数据"
        )

# ==========================================
# 4. 主界面布局 (Main Area)
# ==========================================
st.title("🛡️ 成人用品禁限售治理 - 数据审核工具")

if not st.session_state.data_loaded:
    st.info("👋 欢迎, Neil。请在左侧侧边栏上传 JSONL 文件以开始标注任务。")
else:
    # --- 数据过滤逻辑 ---
    filtered_indices = []
    for idx, item in enumerate(st.session_state.data):
        if selected_status != "All" and item['label'] != selected_status:
            continue
        if str(item.get('search_type')) not in selected_search_type:
            continue
        filtered_indices.append(idx)

    # --- 统计面板 ---
    total = len(st.session_state.data)
    pos = sum(1 for item in st.session_state.data if item['label'] == 'pos')
    neg = sum(1 for item in st.session_state.data if item['label'] == 'neg')
    unlabeled = sum(1 for item in st.session_state.data if item['label'] == 'unlabeled')
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("总样本数", total)
    m2.metric("✅ POS", pos)
    m3.metric("❌ NEG", neg)
    m4.metric("⏳ 待标注", unlabeled)
    
    st.divider()

    # --- 列表展示与翻页 ---
    if not filtered_indices:
        st.warning("没有匹配当前筛选条件的数据。")
    else:
        num_filtered = len(filtered_indices)
        total_pages = (num_filtered - 1) // items_per_page + 1
        page = st.number_input("页码", min_value=1, max_value=total_pages, value=1)
        
        start_ptr = (page - 1) * items_per_page
        end_ptr = min(start_ptr + items_per_page, num_filtered)
        
        for i in range(start_ptr, end_ptr):
            real_idx = filtered_indices[i]
            item = st.session_state.data[real_idx]
            
            with st.container(border=True):
                col_img, col_info, col_btn = st.columns([1, 2, 1])
                
                # 图片展示
                with col_img:
                    url = item['urls'][0] if item.get('urls') else ""
                    if url:
                        st.image(url, use_container_width=True)
                    else:
                        st.error("图片链接缺失")
                
                # 信息展示
                with col_info:
                    st.markdown(f"**Item ID:** `{item.get('item_id', 'N/A')}`")
                    st.markdown(f"**Query:** `{item.get('query', 'N/A')}`")
                    st.text_area("Title", value=item.get('title', ''), height=80, disabled=True)
                    
                    # 状态标签展示
                    label_colors = {"pos": "green", "neg": "red", "disable": "gray", "unlabeled": "blue"}
                    current_lbl = item['label']
                    st.markdown(f"状态: :{label_colors.get(current_lbl, 'blue')}[**{current_lbl.upper()}**]")

                # 操作按钮
                with col_btn:
                    st.write("更新标注:")
                    if st.button("✅ 正样本 (Pos)", key=f"p_{real_idx}", use_container_width=True):
                        update_label(real_idx, "pos")
                    if st.button("❌ 负样本 (Neg)", key=f"n_{real_idx}", use_container_width=True):
                        update_label(real_idx, "neg")
                    if st.button("🚫 禁用 (Disable)", key=f"d_{real_idx}", use_container_width=True):
                        update_label(real_idx, "disable")