import type { VirtualTourRoomTypeOption } from "@/lib/types";

/** Canonical Persian fallback catalog. API configuration remains authoritative when present. */
export const DEFAULT_VIRTUAL_TOUR_ROOM_TYPES: VirtualTourRoomTypeOption[] = [
  { code: "living_room", label: "پذیرایی" },
  { code: "sitting_room", label: "نشیمن" },
  { code: "bedroom", label: "اتاق خواب" },
  { code: "kitchen", label: "آشپزخانه" },
  { code: "bathroom", label: "حمام" },
  { code: "restroom", label: "سرویس بهداشتی" },
  { code: "dining_room", label: "اتاق غذاخوری" },
  { code: "hallway", label: "راهرو" },
  { code: "balcony", label: "بالکن" },
  { code: "terrace", label: "تراس" },
  { code: "yard", label: "حیاط" },
  { code: "parking", label: "پارکینگ" },
  { code: "storage", label: "انباری" },
  { code: "office", label: "دفتر کار" },
  { code: "other", label: "سایر فضاها" },
];

export function roomTypeLabel(option: VirtualTourRoomTypeOption): string {
  return option.label_fa || option.label || option.code;
}
