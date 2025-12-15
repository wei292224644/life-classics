import type { FoodDetail } from "../food/dto";
import type { FoodAiAnalysisCreate, PregnancyLevel, RiskLevel } from "./dto";
import { pregnancyLevel, riskLevel } from "./dto";

/**
 * 通过调用 agent-server 的 /api/chat 接口生成 AI 分析
 */
export class FoodAiAnalysisService {
  private agentServerUrl =
    // eslint-disable-next-line turbo/no-undeclared-env-vars
    process.env.AGENT_SERVER_URL ?? "http://localhost:9999/api/chat";

  public async generateAiAnalysis(
    foodDetail: FoodDetail,
  ): Promise<FoodAiAnalysisCreate> {
    // 默认兜底提示语
    const fallback: FoodAiAnalysisCreate = {
      food_id: foodDetail.id,
      analysis_version: "v1",
      ai_model: "seed-model",
      usage_suggestion_results: ["富含碳水与适量脂肪，适合作为能量补充。"],
      health_benefit_results: ["富含碳水与适量脂肪，适合作为能量补充。"],
      ingredient_analysis_results: ["富含碳水与适量脂肪，适合作为能量补充。"],
      pregnancy_analysis_results: ["富含碳水与适量脂肪，适合作为能量补充。"],
      risk_level: "low",
      pregnancy_level: "low",
      confidence_score: 80,
      raw_output: "fallback: 未能调用 agent-server，返回默认分析摘要。",
      createdByUser: "00000000-0000-0000-0000-000000000000",
    };

    try {
      const message = [
        "# 请基于以下食品信息生成分析结果。",
        `食品名称：${foodDetail.name}`,
        `食品类别：${foodDetail.product_category ?? "未知"}`,
        `食品产地：${foodDetail.origin_place ?? "未知"}`,
        `食品生产商：${foodDetail.manufacturer ?? "未知"}`,
        `食品生产许可：${foodDetail.production_license ?? "未知"}`,
        `食品生产地址：${foodDetail.production_address ?? "未知"}`,
        `食品保质期：${foodDetail.shelf_life ?? "未知"}`,
        `食品净含量：${foodDetail.net_content ?? "未知"}`,
        "食品配料：",
        "| 名称 | 描述 | 是否添加剂 | 添加剂代码 | 国家执行标准 | 风险等级 | 母婴等级 | 过敏信息 | 功能类型 | 来源类型 | 使用限量 |",
        ...foodDetail.ingredients.map(
          (ingredient) =>
            `- ${ingredient.name}|${ingredient.description}|${ingredient.is_additive}|${ingredient.additive_code}|${ingredient.standard_code}|${ingredient.risk_level}|${ingredient.pregnancy_level}|${ingredient.allergen_info}|${ingredient.function_type}|${ingredient.origin_type}|${ingredient.limit_usage}`,
        ),
        "# 分析出以下内容：",
        "- 食用建议摘要:最少3条，最多5条，不要重复，不要出现相同的内容。",
        "- 健康益处摘要:最少3条，最多5条，不要重复，不要出现相同的内容。",
        "- 配料分析摘要:最少3条，最多5条，不要重复，不要出现相同的内容。",
        "- 母婴分析摘要:最少3条，最多5条，不要重复，不要出现相同的内容。",
        `- 风险等级：${riskLevel.options.join(", ")}`,
        `- 母婴等级：${pregnancyLevel.options.join(", ")}`,
        "- 置信度:0-100",
        "- 将上述分析结果总结成一段话",
        "",
        "# 请以json格式返回，返回的json格式为:",
        "{",
        '  "usage_suggestion_results": ["食用建议摘要1", "食用建议摘要2", "食用建议摘要3"],',
        '  "health_benefit_results": ["健康益处摘要1", "健康益处摘要2", "健康益处摘要3"],',
        '  "ingredient_analysis_results": ["配料分析摘要1", "配料分析摘要2", "配料分析摘要3"],',
        '  "pregnancy_analysis_results": ["母婴分析摘要1", "母婴分析摘要2", "母婴分析摘要3"],',
        `  "risk_level": "风险等级", // ${riskLevel.options.join(", ")}`,
        `  "pregnancy_level": "母婴等级", // ${pregnancyLevel.options.join(", ")}`,
        '  "confidence_score": "置信度", // 0-100,',
        '  "raw_output":"分析结果的总结"',
        "}",
      ].join("\n");

      const payload = {
        message,
        conversation_id: `food-${foodDetail.id}-analysis`,
        top_k: 3,
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
        usage_suggestion_results: string[];
        health_benefit_results: string[];
        ingredient_analysis_results: string[];
        pregnancy_analysis_results: string[];
        risk_level: RiskLevel;
        pregnancy_level: PregnancyLevel;
        confidence_score: number;
        raw_output: string;
      };

      return {
        food_id: foodDetail.id,
        analysis_version: "v1",
        ai_model: "agent-server/chat",
        usage_suggestion_results: data.usage_suggestion_results,
        health_benefit_results: data.health_benefit_results,
        ingredient_analysis_results: data.ingredient_analysis_results,
        pregnancy_analysis_results: data.pregnancy_analysis_results,
        risk_level: data.risk_level,
        pregnancy_level: data.pregnancy_level,
        confidence_score: data.confidence_score,
        raw_output: data.raw_output,
        createdByUser: "00000000-0000-0000-0000-000000000000",
      };
    } catch (error) {
      // 记录错误并返回兜底数据
      console.error("generateAiAnalysis failed:", error);
      return fallback;
    }
  }
}

export const foodAiAnalysisService = new FoodAiAnalysisService();
