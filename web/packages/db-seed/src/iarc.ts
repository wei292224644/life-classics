import { db } from "@acme/db/client";
import {
  IarcAgentsTable,
  IarcAgentLinkTable,
} from "@acme/db/schema";
import iarcData from "./iarc_links_chinese.json";

interface SeedResult {
  table: string;
  inserted: number;
}

// 使用一个默认的系统用户 UUID 用于 seed 数据
const SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000000";

interface IarcDataItem {
  "CAS No.": string;
  Agent: string;
  Group: string;
  Volume: string;
  "Volume publication year": string;
  "Evaluation year": string;
  "Additional information": string;
  Links: {
    link: string;
    type: string;
  }[];
  Agent_Chinese: string;
}

async function seedIarcAgents(): Promise<SeedResult> {
  const data = iarcData as IarcDataItem[];

  // 映射 Group 值，空字符串映射到 "unknown"
  const mapGroup = (group: string): "1" | "2A" | "2B" | "3" | "unknown" => {
    if (group === "1" || group === "2A" || group === "2B" || group === "3") {
      return group;
    }
    return "unknown";
  };

  // 准备插入的数据
  const agentRows = data.map((item) => ({
    cas_no: item["CAS No."] || "",
    agent_name: item.Agent,
    zh_agent_name: item.Agent_Chinese || null,
    group: mapGroup(item.Group),
    volume: item.Volume || "",
    volume_publication_year: item["Volume publication year"] || "",
    evaluation_year: item["Evaluation year"] || "",
    additional_information: item["Additional information"] || null,
    createdByUser: SYSTEM_USER_ID,
    updatedByUser: SYSTEM_USER_ID,
  }));

  try {
    // 插入所有 agents
    const insertedAgents = await db
      .insert(IarcAgentsTable)
      .values(agentRows)
      .returning();

    const insertedCount = insertedAgents.length;
    console.log(`Inserted ${insertedCount} IARC agents`);

    // 创建 Agent 名称到 ID 的映射
    const agentNameToId = new Map<string, number>();
    for (const agent of insertedAgents) {
      if (agent.agent_name && agent.id) {
        agentNameToId.set(agent.agent_name, agent.id);
      }
    }

    // 处理 Links 关系
    const linkRows: {
      from_agent_id: number;
      to_agent_id: number;
      link_type: "see" | "see_also";
      createdByUser: string;
      updatedByUser: string;
    }[] = [];

    for (let index = 0; index < data.length; index++) {
      const item = data[index];
      if (!item) continue;
      if (item.Links.length > 0) {
        const fromAgent = insertedAgents[index];
        if (!fromAgent?.id) continue;
        const fromAgentId = fromAgent.id;

        for (const link of item.Links) {
          const toAgentId = agentNameToId.get(link.link);
          if (toAgentId) {
            // 映射 link type，默认为 "see"
            const linkType: "see" | "see_also" =
              link.type === "see_also" ? "see_also" : "see";

            linkRows.push({
              from_agent_id: fromAgentId,
              to_agent_id: toAgentId,
              link_type: linkType,
              createdByUser: SYSTEM_USER_ID,
              updatedByUser: SYSTEM_USER_ID,
            });
          }
        }
      }
    }

    // 插入链接关系
    if (linkRows.length > 0) {
      await db.insert(IarcAgentLinkTable).values(linkRows);
      console.log(`Inserted ${linkRows.length} IARC agent links`);
    }

    return {
      table: "iarc_agents",
      inserted: insertedCount,
    };
  } catch (error: unknown) {
    console.error("Error seeding IARC agents:", error);
    if (error instanceof Error) {
      throw error;
    }
    throw new Error("Unknown error occurred while seeding IARC agents");
  }
}

export { seedIarcAgents };

