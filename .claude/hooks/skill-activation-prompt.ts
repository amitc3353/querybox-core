#!/usr/bin/env node
/**
 * Skill Activation Prompt Hook
 *
 * Analyzes user prompts and file context to automatically activate relevant skills.
 * This is the KEY hook that makes skills actually work automatically.
 */

import * as fs from 'fs';
import * as path from 'path';

interface SkillRule {
  type: string;
  enforcement: string;
  priority: string;
  promptTriggers: {
    keywords: string[];
    intentPatterns: string[];
  };
  fileTriggers: {
    pathPatterns: string[];
    contentPatterns: string[];
  };
}

interface SkillRules {
  [skillName: string]: SkillRule;
}

interface HookContext {
  prompt: string;
  currentFile?: string;
  recentFiles?: string[];
}

/**
 * Main hook function - called by Claude Code on user prompt submit
 */
export async function userPromptSubmit(
  prompt: string,
  context: any
): Promise<string> {
  try {
    // Validate inputs
    if (!prompt || typeof prompt !== 'string') {
      return prompt || '';
    }

    // Ensure context is an object
    if (!context || typeof context !== 'object') {
      context = {};
    }

    // Load skill rules
    const skillRulesPath = path.join(process.cwd(), '.claude/skills/skill-rules.json');

    if (!fs.existsSync(skillRulesPath)) {
      // No skill rules yet, return prompt unchanged
      return prompt;
    }

    const skillRulesContent = fs.readFileSync(skillRulesPath, 'utf-8');
    const skillRules: SkillRules = JSON.parse(skillRulesContent);

    // Check which skills should activate
    const activatedSkills: string[] = [];

    for (const [skillName, rule] of Object.entries(skillRules)) {
      if (shouldActivateSkill(prompt, context, rule)) {
        activatedSkills.push(skillName);
      }
    }

    // If no skills activated, return prompt unchanged
    if (activatedSkills.length === 0) {
      return prompt;
    }

    // Build skill activation message
    const skillList = activatedSkills
      .map(s => `@.claude/skills/${s}.md`)
      .join(', ');

    const reminder = `
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SKILL ACTIVATION CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Relevant skills detected: ${skillList}

Please review these skills before proceeding to ensure consistent patterns.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User request: ${prompt}`;

    return reminder;
  } catch (error) {
    // If hook fails, don't block the user - just return original prompt
    // Silently fail to avoid "hook error" messages in logs
    return prompt;
  }
}

/**
 * Determine if a skill should activate based on prompt and context
 */
function shouldActivateSkill(
  prompt: string,
  context: any,
  rule: SkillRule
): boolean {
  const lowerPrompt = prompt.toLowerCase();

  // Check keyword matches
  for (const keyword of rule.promptTriggers.keywords) {
    if (lowerPrompt.includes(keyword.toLowerCase())) {
      return true;
    }
  }

  // Check intent patterns (regex)
  for (const pattern of rule.promptTriggers.intentPatterns) {
    try {
      if (new RegExp(pattern, 'i').test(prompt)) {
        return true;
      }
    } catch (e) {
      // Invalid regex, skip
      continue;
    }
  }

  // Check file context if available
  if (context && context.currentFile) {
    // Check if current file matches path patterns
    for (const pathPattern of rule.fileTriggers.pathPatterns) {
      const regex = pathPatternToRegex(pathPattern);
      if (regex.test(context.currentFile)) {
        return true;
      }
    }

    // Check if file content matches patterns (if file is readable)
    try {
      if (fs.existsSync(context.currentFile)) {
        const fileContent = fs.readFileSync(context.currentFile, 'utf-8');
        for (const contentPattern of rule.fileTriggers.contentPatterns) {
          try {
            if (new RegExp(contentPattern).test(fileContent)) {
              return true;
            }
          } catch (e) {
            continue;
          }
        }
      }
    } catch (e) {
      // Can't read file, skip content checks
    }
  }

  // Check recent files context
  if (context && context.recentFiles && Array.isArray(context.recentFiles)) {
    for (const file of context.recentFiles) {
      for (const pathPattern of rule.fileTriggers.pathPatterns) {
        const regex = pathPatternToRegex(pathPattern);
        if (regex.test(file)) {
          return true;
        }
      }
    }
  }

  return false;
}

/**
 * Convert glob-like path pattern to regex
 * Example: "backend/api/**\/*.py" -> regex that matches those paths
 */
function pathPatternToRegex(pattern: string): RegExp {
  // Replace ** with .*
  let regexStr = pattern.replace(/\*\*/g, '.*');

  // Replace single * with [^/]*
  regexStr = regexStr.replace(/\*/g, '[^/]*');

  // Escape dots
  regexStr = regexStr.replace(/\./g, '\\.');

  // Add anchors
  regexStr = '^' + regexStr + '$';

  return new RegExp(regexStr);
}

// Export for Claude Code to use
export default {
  userPromptSubmit
};
