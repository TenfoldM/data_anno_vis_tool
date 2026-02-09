import streamlit as st
import pandas as pd
import json
import io
import os

# ==========================================
# 1. 页面配置与状态初始化
# ==========================================
st.set_page_config(layout="wide", page_title="数据标注工具")

# 初始化 session_state 用于存储数据
if 'data' not in st.session_state:
    st.session_state.data = []
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'session_file' not in st.session_state:
    st.session_state.session_file = '.data_anno_session.json'
if 'filter_state' not in st.session_state:
    st.session_state.filter_state = {}

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

                    # 兼容新旧数据结构：统一使用urls字段
                    if 'image_url' in item and 'urls' not in item:
                        item['urls'] = [item['image_url']]

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

def update_gemini_reason(index, new_reason):
    """更新指定索引数据的Gemini Reason"""
    if 'gemini_model_result' not in st.session_state.data[index]:
        st.session_state.data[index]['gemini_model_result'] = {}
    st.session_state.data[index]['gemini_model_result']['reason'] = new_reason
    # 强制重新运行以刷新界面状态
    st.rerun()

def update_gemini_violation_type(index, new_violation_type):
    """更新指定索引数据的Gemini Violation Type"""
    if 'gemini_model_result' not in st.session_state.data[index]:
        st.session_state.data[index]['gemini_model_result'] = {}
    st.session_state.data[index]['gemini_model_result']['violation_type'] = new_violation_type
    # 强制重新运行以刷新界面状态
    st.rerun()

def convert_df_to_jsonl(data):
    """将数据转换为JSONL格式用于下载"""
    jsonl_str = ""
    for item in data:
        jsonl_str += json.dumps(item, ensure_ascii=False) + "\n"
    return jsonl_str

def save_session_state(filter_state):
    """保存会话状态到本地文件"""
    try:
        session_data = {
            'data': st.session_state.data,
            'data_loaded': st.session_state.data_loaded,
            'filter_state': filter_state
        }
        with open(st.session_state.session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"保存会话失败: {e}")
        return False

def load_session_state():
    """从本地文件加载会话状态"""
    try:
        if os.path.exists(st.session_state.session_file):
            with open(st.session_state.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            st.session_state.data = session_data.get('data', [])
            st.session_state.data_loaded = session_data.get('data_loaded', False)
            st.session_state.filter_state = session_data.get('filter_state', {})
            return True
        return False
    except Exception as e:
        st.error(f"加载会话失败: {e}")
        return False

# ==========================================
# 3. 侧边栏布局 (Sidebar)
# ==========================================
with st.sidebar:
    st.header("📂 数据导入与会话管理")

    # 会话管理
    with st.expander("💾 会话管理", expanded=False):
        st.markdown("**保存会话到本地文件：**")
        # 生成会话JSON数据
        if st.session_state.data_loaded:
            session_data = {
                'data': st.session_state.data,
                'data_loaded': st.session_state.data_loaded,
                'filter_state': st.session_state.filter_state
            }
            session_json = json.dumps(session_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="📥 下载会话文件",
                data=session_json,
                file_name="data_anno_session.json",
                mime="application/json",
                help="下载会话文件到本地电脑"
            )
        else:
            st.info("请先加载数据后再保存会话")

        st.divider()
        st.markdown("**从本地文件加载会话：**")
        session_upload = st.file_uploader("上传会话文件", type=['json'], key="session_uploader")
        if session_upload is not None:
            try:
                session_data = json.load(session_upload)
                st.session_state.data = session_data.get('data', [])
                st.session_state.data_loaded = session_data.get('data_loaded', False)
                st.session_state.filter_state = session_data.get('filter_state', {})
                st.success("会话加载成功！")
                st.rerun()
            except Exception as e:
                st.error(f"加载会话失败: {e}")

    st.divider()

    uploaded_file = st.file_uploader("上传 JSONL 文件", type=['jsonl', 'json'])

    if uploaded_file and not st.session_state.data_loaded:
        load_data(uploaded_file)
    
    # 仅当数据加载后显示筛选器
    if st.session_state.data_loaded:
        st.divider()
        st.header("🔍 筛选条件")

        # 从保存的filter_state中获取默认值
        saved_filter = st.session_state.filter_state

        # 1. 标注状态筛选
        status_options = ["All", "unlabeled", "pos", "neg", "disable"]
        default_status_index = status_options.index(saved_filter.get('selected_status', 'All')) if saved_filter.get('selected_status') in status_options else 0
        selected_status = st.selectbox("标注状态 (Label Status)", status_options, index=default_status_index)

        # 2. 搜索类型筛选 (根据数据动态获取)
        all_search_types = list(set([item.get('search_type', 'Unknown') for item in st.session_state.data]))
        default_search_types = saved_filter.get('selected_search_type', all_search_types)
        # 确保default_search_types中的所有项都在all_search_types中
        default_search_types = [st for st in default_search_types if st in all_search_types]
        if not default_search_types:
            default_search_types = all_search_types
        selected_search_type = st.multiselect("Search Type", all_search_types, default=default_search_types)

        # 3. Violation Type 筛选
        all_violation_types = list(set([
            item.get('gemini_model_result', {}).get('violation_type', 'None')
            for item in st.session_state.data
        ]))
        # 移除空值并排序
        all_violation_types = sorted([vt for vt in all_violation_types if vt and vt != 'None'])
        all_violation_types = ["All"] + all_violation_types
        default_violation_type = saved_filter.get('selected_violation_type', 'All')
        default_vt_index = all_violation_types.index(default_violation_type) if default_violation_type in all_violation_types else 0
        selected_violation_type = st.selectbox("Violation Type", all_violation_types, index=default_vt_index)

        # 4. ID 范围筛选
        total_count = len(st.session_state.data)
        if total_count > 0:
            default_id_range = saved_filter.get('id_range', (1, total_count))
            # 确保范围有效
            default_id_range = (
                max(1, min(default_id_range[0], total_count)),
                max(1, min(default_id_range[1], total_count))
            )
            id_range = st.slider("Item ID 范围", 1, total_count, default_id_range)
        else:
            id_range = (0, 0)

        # 5. 每页显示数量
        default_items_per_page = saved_filter.get('items_per_page', 10)
        items_per_page = st.slider("每页条数", 5, 50, default_items_per_page)

        # 更新filter_state以便保存
        st.session_state.filter_state = {
            'selected_status': selected_status,
            'selected_search_type': selected_search_type,
            'selected_violation_type': selected_violation_type,
            'id_range': id_range,
            'items_per_page': items_per_page
        }
        
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
        # Violation Type 过滤
        if selected_violation_type != "All":
            item_violation_type = item.get('gemini_model_result', {}).get('violation_type', 'None')
            if item_violation_type != selected_violation_type:
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
            st.markdown(f"**筛选结果:** {len(filtered_data)} 条数据，共 {total_pages} 页")
            default_page = st.session_state.filter_state.get('current_page', 1)
            # 确保页码在有效范围内
            default_page = max(1, min(default_page, total_pages))
            current_page = st.number_input("页码", min_value=1, max_value=total_pages, value=default_page)
            # 保存当前页码
            st.session_state.filter_state['current_page'] = current_page
        
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
                        # 获取图片URL，优先使用image_url，失败时使用image_thumbnail
                        img_url = None
                        img_thumbnail = None

                        if item.get('urls'):
                            img_url = item['urls'][0]
                        elif item.get('image_url'):
                            img_url = item['image_url']

                        if item.get('image_thumbnail'):
                            img_thumbnail = item['image_thumbnail']

                        # 尝试显示主图片，失败时显示缩略图
                        image_displayed = False
                        if img_url:
                            try:
                                st.image(img_url, width=150)
                                image_displayed = True
                            except:
                                pass

                        if not image_displayed and img_thumbnail:
                            try:
                                st.image(img_thumbnail, width=150)
                                image_displayed = True
                            except:
                                pass

                        if not image_displayed:
                            st.text("No Image")

                    with sub_c2:
                        st.markdown(f"**Item ID:** {item.get('item_id', 'N/A')}")
                        st.markdown(f"**Search Type:** `{item.get('search_type', '-')}`")
                        st.markdown(f"**Query:** `{item.get('query', '-')}`")
                        st.markdown(f"**Title:** {item.get('title', '-')}")

                        # 显示Gemini模型结果
                        gemini_result = item.get('gemini_model_result', {})
                        if gemini_result:
                            if gemini_result.get('violation_type'):
                                current_violation_type = gemini_result.get('violation_type', '')
                                col_vt1, col_vt2 = st.columns([3, 1])
                                with col_vt1:
                                    edited_violation_type = st.text_input(
                                        "Violation Type",
                                        value=current_violation_type,
                                        key=f"vtype_edit_{real_index}"
                                    )
                                with col_vt2:
                                    st.write("")  # 占位，对齐按钮
                                    if st.button("💾", key=f"btn_save_vtype_{real_index}", help="保存Violation Type修改"):
                                        if edited_violation_type != current_violation_type:
                                            update_gemini_violation_type(real_index, edited_violation_type)
                            if gemini_result.get('reason'):
                                with st.expander("🤖 Gemini Reason (可编辑)", expanded=False):
                                    current_reason = gemini_result.get('reason', '')
                                    edited_reason = st.text_area(
                                        "编辑原因:",
                                        value=current_reason,
                                        height=150,
                                        key=f"reason_edit_{real_index}"
                                    )
                                    if st.button("💾 保存修改", key=f"btn_save_reason_{real_index}"):
                                        if edited_reason != current_reason:
                                            update_gemini_reason(real_index, edited_reason)
                                            st.success("已保存修改！")

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
