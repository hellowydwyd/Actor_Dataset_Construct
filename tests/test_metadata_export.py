#!/usr/bin/env python3
"""
测试metadata导出功能
"""
import sys
import requests
import json
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_metadata_export(base_url="http://localhost:5000"):
    """测试metadata导出功能"""
    
    print("🧪 测试metadata导出功能...")
    
    try:
        # 测试导出API
        response = requests.get(f"{base_url}/api/export_metadata")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                export_data = data.get('data', {})
                print(f"✅ 导出成功!")
                print(f"   - 导出时间: {export_data.get('export_time')}")
                print(f"   - 数据库类型: {export_data.get('database_type')}")
                print(f"   - 记录总数: {export_data.get('total_records')}")
                print(f"   - metadata条目数: {len(export_data.get('metadata', []))}")
                
                # 保存到文件进行验证
                output_file = Path("test_metadata_export.json")
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, ensure_ascii=False, indent=2)
                
                print(f"   - 测试文件已保存: {output_file}")
                
                # 显示部分metadata示例
                metadata_list = export_data.get('metadata', [])
                if metadata_list:
                    print(f"\n📋 Metadata示例 (前3条):")
                    for i, meta in enumerate(metadata_list[:3]):
                        print(f"   {i+1}. 角色: {meta.get('character', 'Unknown')}")
                        print(f"      演员: {meta.get('actor_name', 'Unknown')}")
                        print(f"      电影: {meta.get('movie_title', 'Unknown')}")
                        print(f"      人脸ID: {meta.get('face_id', 'Unknown')}")
                        print(f"      检测分数: {meta.get('det_score', 0):.3f}")
                        print()
                
            else:
                print(f"❌ API返回错误: {data.get('error')}")
                
        else:
            print(f"❌ HTTP请求失败: {response.status_code}")
            print(f"   响应内容: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保Web服务已启动")
        print("   运行命令: python main.py web")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")


def main():
    """主函数"""
    print("🎬 Metadata导出功能测试")
    print("=" * 50)
    
    # 测试本地服务器
    test_metadata_export()
    
    print("\n" + "=" * 50)
    print("测试完成!")


if __name__ == "__main__":
    main()
