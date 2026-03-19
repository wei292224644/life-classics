import type { FoodDetail } from "../food/type";
import type { AnalysisDetailCreate, AnalysisLevel, AnalysisType } from "./type";

/**
 * 通过调用 agent-server 的 /api/chat 接口生成 AI 分析
 */
export class FoodAiAnalysisService {
  private agentServerUrl =
    // eslint-disable-next-line turbo/no-undeclared-env-vars
    process.env.AGENT_SERVER_URL ?? "http://localhost:9999/api/chat";

  public async generateAiAnalysisList(
    foodDetail: FoodDetail,
  ): Promise<AnalysisDetailCreate[]> {
    // 默认兜底提示语

    try {
      const message = `你是一名专业的食品安全、营养学与母婴健康分析专家。
         你的分析结果将被直接存入数据库中的食品分析表。
        【分析原则】
        1. 每一个分析维度都必须独立判断风险等级（t0–t4）
        2. 各分析维度之间不得互相引用结论
        3. 如信息不足，请明确标记为 uncertain
        4. 严禁编造风险、处罚记录或新闻事件
        5. 母婴分析需采用更严格的安全标准

        ---

        【输入数据】
        以下是${foodDetail.name}的结构化信息（字段可能不完整）：

        食品名称：${foodDetail.name}
        食品类别：${foodDetail.product_category ?? "未知"}
        食品产地：${foodDetail.origin_place ?? "未知"}
        食品生产商：${foodDetail.manufacturer ?? "未知"}
        食品生产许可：${foodDetail.production_license ?? "未知"}
        食品生产地址：${foodDetail.production_address ?? "未知"}
        食品保质期：${foodDetail.shelf_life ?? "未知"}
        食品净含量：${foodDetail.net_content ?? "未知"}
        食品配料：
        | 名称 | 描述 | 是否添加剂 | 添加剂代码 | 国家执行标准 | WHO致癌等级 | 过敏信息 | 功能来源 | 来源类型 | 使用限量 |
        ${foodDetail.ingredients.map((ingredient) => ingredient.name + " | " + ingredient.description + " | " + ingredient.is_additive + " | " + ingredient.additive_code + " | " + ingredient.standard_code + " | " + ingredient.who_level + " | " + ingredient.allergen_info + " | " + ingredient.function_type + " | " + ingredient.origin_type + " | " + ingredient.limit_usage).join(" | " + "\n")}
        | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |

        ---

        【分析维度（必须全部生成）】
        你需要针对同一个 food_id，分别生成 **5 条独立的分析结果**：

        1. usage（食用建议，最少3条，最多5条，不要重复，不要出现相同的内容。）
        2. health（健康分析，最少3条，最多5条，不要重复，不要出现相同的内容。）
        3. ingredient（配料分析，最少3条，最多5条，不要重复，不要出现相同的内容。）
        4. pregnancy（母婴分析，最少3条，最多5条，不要重复，不要出现相同的内容。）
        5. risk（风险分析，包含食品本身 + 生产厂商/关联公司，时间跨度可以来到最近1年，注意食品安全事件的时效性，不要使用过时的数据。如果没有食品安全事故，则输出为空数组。）

        ---

      【风险等级定义（level）】
      - t0：未发现风险，信息充分
      - t1：轻微注意点
      - t2：明确争议或潜在风险
      - t3：较高风险，需要警示
      - t4：严重风险，不建议食用
      - unknown：信息不足

      ---

      【置信度说明（confidence_score）】
      - 90-100：高度可靠
      - 70-89：较可靠
      - 40-69：信息有限
      - 0-39：严重不足

      ---

      【输出要求】
      输出一个 JSON格式的字符串，不要输出任何其他内容。
      结构必须完全一致如下：
      {
        model:"",//使用的AI模型，
        //分析结果，数组类型，每个元素为一条分析结果，必须包含5条分析结果，每条分析结果的结构必须完全一致。
        results:[
          {
            analysis_type: "", //分析类型，usage | health | ingredient | pregnancy | risk
            summaries: [], //分析结果摘要，数组类型，每个元素为一条分析结果的摘要
            level: "", //风险等级，t0 | t1 | t2 | t3 | t4 | unknown
            confidence_score: 0, //置信度，0-100
            raw_output: {
              summary: "", //分析结果的总结
              key_points: [], //关键点
              uncertainties: [] //不确定点
            }
          }
        ]
      }`;

      const payload = {
        message,
        top_k: 5,
      };

      const response = await fetch(this.agentServerUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`agent-server chat error: ${response.status}`);
      }

      const raw_data = (await response.json()) as {
        answer: string;
      };
      const data = JSON.parse(raw_data.answer) as {
        model: string;
        results: {
          analysis_type: AnalysisType;
          summaries: string[];
          level: AnalysisLevel;
          confidence_score: number;
          raw_output: {
            summary: string;
            key_points: string[];
            uncertainties: string[];
          };
        }[];
      };

      const analysisList: AnalysisDetailCreate[] = [];

      for (const result of data.results) {
        analysisList.push({
          target_id: foodDetail.id,
          target_type: "food",
          analysis_type: result.analysis_type,
          analysis_version: "v1",
          ai_model: data.model,
          results: result.summaries,
          level: result.level,
          confidence_score: result.confidence_score,
          raw_output: result.raw_output,
        });
      }
      return analysisList;
    } catch (error) {
      // 记录错误并返回兜底数据
      console.error("generateAiAnalysis failed:", error);

      throw new Error("generateAiAnalysis failed");
    }
  }
}

export const foodAiAnalysisService = new FoodAiAnalysisService();
