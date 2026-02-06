import streamlit as st
import pandas as pd
import json
import io

# ==========================================
# 1. 页面配置与状态初始化
# ==========================================
st.set_page_config(layout="wide", page_title="数据标注工具")

# 初始化 session_state 用于存储数据
if 'data' not in st.session_state:
    st.session_state.data = []
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False

# ==========================================
# 2. 核心功能函数
# ==========================================
def load_data(uploaded_file):
    """读取上传的JSONL文件并存入session_state"""
    if uploaded_file is not None:
        try:
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
            st.success(f"成功加载 {len(data_list)} 条数据！")
        except Exception as e:
            st.error(f"文件读取失败: {e}")

def update_label(index, new_label):
    """更新指定索引数据的标签"""
    st.session_state.data[index]['label'] = new_label
    # 强制重新运行以刷新界面状态
    st.rerun()

def convert_df_to_jsonl(data):
    """将数据转换为JSONL格式用于下载"""
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
    
    # 仅当数据加载后显示筛选器
    if st.session_state.data_loaded:
        st.divider()
        st.header("🔍 筛选条件")
        
        # 1. 标注状态筛选
        status_options = ["All", "unlabeled", "pos", "neg", "disable"]
        selected_status = st.selectbox("标注状态 (Label Status)", status_options)
        
        # 2. 搜索类型筛选 (根据数据动态获取)
        all_search_types = list(set([item.get('search_type', 'Unknown') for item in st.session_state.data]))
        selected_search_type = st.multiselect("Search Type", all_search_types, default=all_search_types)
        
        # 3. ID 范围筛选
        total_count = len(st.session_state.data)
        if total_count > 0:
            id_range = st.slider("Item ID 范围", 1, total_count, (1, total_count))
        else:
            id_range = (0, 0)
            
        # 4. 每页显示数量
        items_per_page = st.slider("每页条数", 5, 50, 10)
        
        st.divider()
        st.header("💾 结果导出")
        # 导出按钮
        if st.session_state.data_loaded:
            jsonl_data = convert_df_to_jsonl(st.session_state.data)
            st.download_button(
                label="📥 下载标注结果 (JSONL)",
                data=jsonl_data,
                file_name="labeled_data.jsonl",
                mime="application/json"
            )

# ==========================================
# 4. 主界面布局 (Main Area)
# ==========================================
st.title("🔍 数据标注工具")

if not st.session_state.data_loaded:
    st.info("👈 请在左侧上传 JSONL 文件开始工作")
else:
    # --- 数据过滤逻辑 ---
    filtered_data = []
    # 这里为了保留原始索引方便修改，我们存储 (index, item) 元组
    for idx, item in enumerate(st.session_state.data):
        # 状态过滤
        if selected_status != "All" and item['label'] != selected_status:
            continue
        # Search Type 过滤
        if item.get('search_type') not in selected_search_type:
            continue
        # ID 范围过滤 (假设数据按顺序排列，或者简单使用 enumerate 的 index+1 作为 ID)
        current_id = idx + 1 # 或者使用 item['item_id'] 如果它是连续整数
        if not (id_range[0] <= current_id <= id_range[1]):
            continue
            
        filtered_data.append((idx, item))

    # --- 统计面板 ---
    total_samples = len(st.session_state.data)
    pos_count = sum(1 for item in st.session_state.data if item['label'] == 'pos')
    neg_count = sum(1 for item in st.session_state.data if item['label'] == 'neg')
    disable_count = sum(1 for item in st.session_state.data if item['label'] == 'disable')
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("总样本", total_samples)
    col2.metric("✅ Pos", pos_count)
    col3.metric("❌ Neg", neg_count)
    col4.metric("🚫 Disable", disable_count)
    
    st.divider()

    # --- 分页逻辑 ---
    if len(filtered_data) == 0:
        st.warning("没有符合筛选条件的数据。")
    else:
        # 计算页码
        total_pages = (len(filtered_data) - 1) // items_per_page + 1
        
        # 在侧边栏增加页码选择，或者在底部
        with st.sidebar:
            current_page = st.number_input("页码", min_value=1, max_value=total_pages, value=1)
        
        start_idx = (current_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, len(filtered_data))
        
        current_batch = filtered_data[start_idx:end_idx]

        # --- 列表渲染 ---
        for real_index, item in current_batch:
            with st.container():
                # 每一行分两列：左边图+信息，右边按钮组
                c1, c2 = st.columns([3, 1])
                
                with c1:
                    # 显示图片和元数据
                    sub_c1, sub_c2 = st.columns([1, 2])
                    with sub_c1:
                        # 获取第一张图片，如果没有则显示占位
                        img_url = item['urls'][0] if item.get('urls') else None
                        if img_url:
                            st.image(img_url, width=150)
                        else:
                            st.text("No Image")
                    
                    with sub_c2:
                        st.markdown(f"**Item ID:** {item.get('item_id', 'N/A')}")
                        st.markdown(f"**Search Type:** `{item.get('search_type', '-')}`")
                        st.markdown(f"**Query:** `{item.get('query', '-')}`")
                        st.markdown(f"**Title:** {item.get('title', '-')}")
                        # 显示当前状态的徽章
                        status_color = {
                            "pos": "green", "neg": "red", "disable": "gray", "unlabeled": "blue"
                        }
                        color = status_color.get(item['label'], "blue")
                        st.markdown(f"当前状态: :{color}[**{item['label'].upper()}**]")

                with c2:
                    st.write("标注操作:")
                    # 使用唯一 key 避免冲突
                    if st.button("✅ Pos", key=f"btn_pos_{real_index}"):
                        update_label(real_index, "pos")
                    
                    if st.button("❌ Neg", key=f"btn_neg_{real_index}"):
                        update_label(real_index, "neg")
                        
                    if st.button("🚫 Disable", key=f"btn_dis_{real_index}"):
                        update_label(real_index, "disable")

                st.divider()
