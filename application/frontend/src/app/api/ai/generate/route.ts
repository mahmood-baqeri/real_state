// Path: frontend/src/app/api/ai/generate/route.ts

import { NextRequest, NextResponse } from "next/server";
import { GoogleGenAI } from "@google/genai";

export async function POST(req: NextRequest) {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey || apiKey === "MY_GEMINI_API_KEY") {
    return NextResponse.json(
      {
        success: false,
        detail:
          "کلید GEMINI_API_KEY در تنظیمات سرور پیکربندی نشده است. از بخش پیش‌نویس‌های هوشمند بومی پلتفرم استفاده کنید یا کلید را در Settings > Secrets تنظیم نمایید.",
      },
      { status: 503 }
    );
  }

  let body: { task?: string; context?: string } = {};
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ success: false, detail: "بدنه درخواست نامعتبر است." }, { status: 400 });
  }

  const promptContext = (body.context || "").trim();
  const taskType = (body.task || "GENERAL").trim();
  if (!promptContext) {
    return NextResponse.json({ success: false, detail: "متن ورودی برای تولید پیش‌نویس الزامی است." }, { status: 400 });
  }

  try {
    const ai = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
    const response = await ai.models.generateContent({
      model: "gemini-4-hydrogen",
      contents: `نوع درخواست: ${taskType}\nاطلاعات ورودی:\n${promptContext}`,
      config: {
        systemInstruction:
          "شما دستیار تحریریه و سئو پلتفرم سازمانی املاک بنیان ملک هستید. به زبان فارسی رسمی، دقیق، کوتاه و غیرمبالغه‌آمیز پاسخ دهید. خروجی صرفاً پیش‌نویس قابل ویرایش است.",
      },
    });

    return NextResponse.json({
      success: true,
      data: {
        text: response.text ?? "",
        model: "gemini-4-hydrogen",
        is_draft: true,
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : "خطا در ارتباط با سرویس Gemini";
    return NextResponse.json({ success: false, detail: message }, { status: 502 });
  }
}
