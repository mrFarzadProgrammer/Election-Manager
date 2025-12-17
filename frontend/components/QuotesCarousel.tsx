import React, { useState, useEffect } from 'react';
import { Quote } from 'lucide-react';

const QUOTES = [
  { id: 1, text: "میزان رأی ملت است.", author: "امام خمینی (ره)", role: "بنیانگذار انقلاب اسلامی" },
  { id: 2, text: "انتخابات مظهر اقتدار ملی است؛ اگر اقتدار ملی نبود، امنیت ملی هم نخواهد بود.", author: "مقام معظم رهبری", role: "رهبر انقلاب" },
  { id: 3, text: "باید همه شما در انتخابات شرکت کنید؛ تکلیف شرعی است.", author: "امام خمینی (ره)", role: "بنیانگذار انقلاب اسلامی" },
  { id: 4, text: "علاج دردهای مزمن کشور در پرشور بودن انتخابات و در حضور عمومی مردم است.", author: "مقام معظم رهبری", role: "رهبر انقلاب" },
  { id: 5, text: "انتخابات در انحصار هیچ کس نیست، نه در انحصار روحانیین است، نه در انحصار احزاب است.", author: "امام خمینی (ره)", role: "بنیانگذار انقلاب اسلامی" },
  { id: 6, text: "حضور مردم در پای صندوق های رأی، مصون ساز سرنوشت ملت و مردم است.", author: "مقام معظم رهبری", role: "رهبر انقلاب" },
  { id: 7, text: "نگویید که دیگران رأی می دهند. من هم باید رأی بدهم، تو هم باید رأی بدهی.", author: "امام خمینی (ره)", role: "بنیانگذار انقلاب اسلامی" },
  { id: 8, text: "انتخابات یک نوسازی در کشور است؛ وارد شدن یک نَفَس تازه است.", author: "مقام معظم رهبری", role: "رهبر انقلاب" },
  { id: 9, text: "سرنوشت اسلام و کشور خود را با عدم حضور و یا حضور بی تفاوت و دلسرد کننده به دست کسانی ندهید که به اسلام و ایران فکر نمی کنند.", author: "امام خمینی (ره)", role: "بنیانگذار انقلاب اسلامی" },
  { id: 10, text: "هر رای مردم، تیری به قلب دشمنان ایران و اسلام است.", author: "مقام معظم رهبری", role: "رهبر انقلاب" },
];

interface QuotesCarouselProps {
  variant?: 'fullscreen' | 'widget';
}

export default function QuotesCarousel({ variant = 'fullscreen' }: QuotesCarouselProps) {
  const [current, setCurrent] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((prev) => (prev + 1) % QUOTES.length);
    }, 5000); 
    return () => clearInterval(timer);
  }, []);

  const isWidget = variant === 'widget';

  return (
    <div className={`relative w-full h-full flex flex-col justify-center items-center text-white overflow-hidden bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 ${isWidget ? 'p-6' : 'p-12'}`}>
      {/* Background decoration */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-white/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>
      <div className="absolute bottom-0 left-0 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl translate-y-1/2 -translate-x-1/2"></div>

      {/* Quote Icon */}
      <div className={`absolute left-6 opacity-20 ${isWidget ? 'top-2 scale-50' : 'top-12'}`}>
        <Quote size={isWidget ? 60 : 120} />
      </div>

      <div className="z-10 max-w-2xl text-center space-y-4 animate-fade-in transition-all duration-700 ease-in-out flex flex-col items-center justify-center h-full" key={current}>
        <p className={`${isWidget ? 'text-lg line-clamp-3' : 'text-2xl md:text-4xl'} font-bold leading-relaxed font-[Vazirmatn] drop-shadow-lg`}>
          «{QUOTES[current].text}»
        </p>
        <div className="flex flex-col items-center gap-1 mt-auto">
            <div className={`bg-yellow-400 rounded-full mb-1 ${isWidget ? 'w-8 h-0.5' : 'w-16 h-1'}`}></div>
            <h3 className={`${isWidget ? 'text-sm' : 'text-xl'} font-bold text-yellow-100`}>{QUOTES[current].author}</h3>
            {!isWidget && <span className="text-sm text-blue-200">{QUOTES[current].role}</span>}
        </div>
      </div>

      {/* Indicators */}
      {!isWidget && (
          <div className="absolute bottom-12 flex gap-2">
            {QUOTES.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrent(idx)}
                className={`transition-all duration-300 rounded-full ${
                  idx === current ? 'w-8 h-2 bg-yellow-400' : 'w-2 h-2 bg-white/30 hover:bg-white/50'
                }`}
              />
            ))}
          </div>
      )}
    </div>
  );
}