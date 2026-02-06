import streamlit as st
import pandas as pd
import json
import io
import datetime

# ==========================================
# 1. 页面配置与初始化
# ==========================================
st.set_page_config(layout="wide", page_title="标注与可视化工具")

# 初始化 session_state
if 'data' not in st.session_state:
    st.session_state.data = []
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'original_filename' not in st.session_state:
    st.session_state.original_filename = "data"
# 初始化页码状态
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

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
                    # 确保每个item都有label字段
                    if 'label' not in item or not item['label']:
                        item['label'] = 'unlabeled'
                    data_list.append(item)
            
            st.session_state.data = data_list
            st.session_state.data_loaded = True
            # 重置页码为1
            st.session_state.current_page = 1
        except Exception as e:
            st.error(f"文件读取失败: {e}")

def update_label(index, new_label):
    """更新指定索引数据的标签"""
    st.session_state.data[index]['label'] = new_label
    # Streamlit 会自动重运行以刷新界面

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
    uploaded_file = st.file_uploader("上传 JSONL 文件", type=['jsonl', 'json'])
    
    if uploaded_file and not st.session_state.data_loaded:
        load_data(uploaded_file)
    
    if st.session_state.data_loaded:
        st.divider()
        st.header("🔍 筛选与控制")
        
        # 1. 标注状态筛选
        status_options = ["All", "unlabeled", "pos", "neg", "disable"]
        selected_status = st.selectbox("筛选标注状态", status_options)
        
        # 2. 搜索类型筛选
        all_search_types = list(set([str(item.get('search_type', 'Unknown')) for item in st.session_state.data]))
        selected_search_type = st.multiselect("筛选 Search Type", all_search_types, default=all_search_types)
        
        # 3. 每页数量设置
        items_per_page = st.slider("每页显示条数", 5, 50, 10)
        
        st.divider()
        st.header("💾 结果导出")
        
        # 动态文件名生成
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"{st.session_state.original_filename}_{timestamp}_labeled_data.jsonl"
        
        jsonl_output = convert_to_jsonl(st.session_state.data)
        st.download_button(
            label="📥 下载标注结果 (JSONL)",
            data=jsonl_output,
            file_name=export_filename,
            mime="application/json",
            help="导出当前所有数据（包含最新标注状态）"
        )

# ==========================================
# 4. 主界面布局 (Main Area)
# ==========================================
st.title("🛡️ 成人用品数据审核工具")

if not st.session_state.data_loaded:
    st.info("👈 请在左侧上传数据文件开始工作")
else:
    # --- 数据过滤逻辑 ---
    filtered_indices = []
    for idx, item in enumerate(st.session_state.data):
        # 状态过滤
        if selected_status != "All" and item['label'] != selected_status:
            continue
        # Search Type 过滤
        if str(item.get('search_type')) not in selected_search_type:
            continue
        filtered_indices.append(idx)

    # --- 统计面板 ---
    total = len(st.session_state.data)
    pos = sum(1 for item in st.session_state.data if item['label'] == 'pos')
    neg = sum(1 for item in st.session_state.data if item['label'] == 'neg')
    unlabeled = sum(1 for item in st.session_state.data if item['label'] == 'unlabeled')
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("总样本", total)
    m2.metric("✅ POS", pos)
    m3.metric("❌ NEG", neg)
    m4.metric("⏳ 待标注", unlabeled)
    
    st.divider()

    # --- 列表渲染与分页逻辑 ---
    if not filtered_indices:
        st.warning("没有匹配当前筛选条件的数据。")
    else:
        num_filtered = len(filtered_indices)
        total_pages = (num_filtered - 1) // items_per_page + 1
        
        # 边界检查：确保当前页码有效
        if st.session_state.current_page > total_pages:
            st.session_state.current_page = total_pages
        if st.session_state.current_page < 1:
            st.session_state.current_page = 1

        # [Top Pagination] 顶部页码输入框
        col_top_1, col_top_2 = st.columns([1, 6])
        with col_top_1:
            # 直接绑定到 session_state.current_page
            st.number_input(
                "跳转页码", 
                min_value=1, 
                max_value=total_pages, 
                key="current_page" 
            )
        
        # 计算当前页数据的起止索引
        start_ptr = (st.session_state.current_page - 1) * items_per_page
        end_ptr = min(start_ptr + items_per_page, num_filtered)
        
        # 渲染当前页的数据卡片
        for i in range(start_ptr, end_ptr):
            real_idx = filtered_indices[i]
            item = st.session_state.data[real_idx]
            
            with st.container(border=True):
                col_img, col_info, col_btn = st.columns([1, 2, 1])
                
                # 1. 图片展示
                with col_img:
                    url = item['urls'][0] if item.get('urls') else ""
                    if url:
                        st.image(url, use_container_width=True)
                    else:
                        st.text("无图片")
                
                # 2. 信息展示
                with col_info:
                    st.markdown(f"**Item ID:** `{item.get('item_id', 'N/A')}`")
                    st.markdown(f"**Query:** `{item.get('query', 'N/A')}`")
                    # 使用 text_area 显示标题，避免过长
                    st.text_area("Title", value=item.get('title', ''), height=70, disabled=True, key=f"title_{real_idx}")
                    
                    # 状态展示
                    label_colors = {"pos": "green", "neg": "red", "disable": "gray", "unlabeled": "blue"}
                    current_lbl = item['label']
                    st.markdown(f"当前状态: :{label_colors.get(current_lbl, 'blue')}[**{current_lbl.upper()}**]")

                # 3. 操作按钮
                with col_btn:
                    st.write("更新标注:")
                    if st.button("✅ Pos", key=f"p_{real_idx}", use_container_width=True):
                        update_label(real_idx, "pos")
                    if st.button("❌ Neg", key=f"n_{real_idx}", use_container_width=True):
                        update_label(real_idx, "neg")
                    if st.button("🚫 Disable", key=f"d_{real_idx}", use_container_width=True):
                        update_label(real_idx, "disable")

        # --- [Bottom Pagination] 底部翻页按钮 ---
        st.divider()
        
        # 回调函数：处理按钮点击
        def prev_page():
            st.session_state.current_page -= 1
        def next_page():
            st.session_state.current_page += 1

        b_col1, b_col2, b_col3 = st.columns([1, 8, 1])
        
        # 上一页按钮
        with b_col1:
            if st.session_state.current_page > 1:
                st.button("⬅️ 上一页", on_click=prev_page, use_container_width=True)
        
        # 进度文本
        with b_col2:
            st.markdown(f"<center style='line-height: 2.5;'>第 {st.session_state.current_page} / {total_pages} 页</center>", unsafe_allow_html=True)
            
        # 下一页按钮
        with b_col3:
            if st.session_state.current_page < total_pages:
                st.button("下一页 ➡️", on_click=next_page, use_container_width=True)