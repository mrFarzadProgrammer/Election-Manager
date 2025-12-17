import React, { useState } from 'react';
import { CandidateData } from '../types';
import { Send, Menu, Bot, User, MapPin, FileText, Mic, Play } from 'lucide-react';

interface BotPreviewProps {
  candidate: CandidateData;
}

const BotPreview: React.FC<BotPreviewProps> = ({ candidate }) => {
  const [activeMessage, setActiveMessage] = useState<string | null>("خوش آمدید! برای شروع یکی از گزینه‌ها را انتخاب کنید.");
  const [msgType, setMsgType] = useState<'TEXT' | 'IMAGE' | 'AUDIO'>('TEXT');

  const handleCommand = (cmd: string, content: string | undefined, type: 'TEXT' | 'IMAGE' | 'AUDIO' = 'TEXT') => {
    setActiveMessage(content || "اطلاعاتی ثبت نشده است.");
    setMsgType(content ? type : 'TEXT');
  };

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div className="w-[320px] h-[600px] bg-gray-100 rounded-[3rem] border-8 border-gray-800 shadow-2xl overflow-hidden relative flex flex-col">
        {/* Dynamic Island / Notch */}
        <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-32 h-6 bg-gray-800 rounded-b-xl z-20"></div>

        {/* Telegram Header */}
        <div className="bg-[#517da2] text-white p-3 pt-8 flex items-center shadow-sm z-10">
          <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center mr-2 overflow-hidden">
            {candidate.photoUrl ? (
                <img src={candidate.photoUrl} alt="Profile" className="w-full h-full object-cover" />
            ) : (
                <Bot size={24} />
            )}
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-sm">{candidate.botName}</span>
            <span className="text-[10px] opacity-80">bot</span>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 p-3 overflow-y-auto bg-[#8bb5ce]/20 bg-[url('https://web.telegram.org/img/bg_0.png')]">
          {/* Incoming Message */}
          <div className="flex flex-col space-y-2">
            <div className="self-start bg-white rounded-lg rounded-tl-none p-3 shadow-sm max-w-[85%] text-sm text-gray-800 relative">
               
               {/* Text Content */}
               {msgType === 'TEXT' && activeMessage}

               {/* Image Content */}
               {msgType === 'IMAGE' && activeMessage && (
                   <div className="flex flex-col">
                       <img src={activeMessage} alt="Candidate" className="rounded-lg w-full h-40 object-cover mb-1" />
                       <span className="text-xs text-gray-600 mt-1">تصویر ارسالی بات</span>
                   </div>
               )}

               {/* Audio Content */}
               {msgType === 'AUDIO' && activeMessage && (
                   <div className="flex items-center gap-3 w-48">
                       <div className="w-10 h-10 bg-blue-500 rounded-full flex items-center justify-center text-white shrink-0">
                           <Play size={20} fill="white" />
                       </div>
                       <div className="flex flex-col flex-1">
                           <span className="text-blue-500 font-bold text-xs">Voice Message</span>
                           <div className="h-1 bg-gray-300 rounded-full mt-1 w-full"></div>
                           <span className="text-[10px] text-gray-400 mt-0.5">0:15</span>
                       </div>
                       {/* Hidden audio element for functionality if needed */}
                       <audio src={activeMessage} className="hidden" />
                   </div>
               )}

               <span className="text-[10px] text-gray-400 absolute bottom-1 right-2">12:00</span>
            </div>
          </div>
        </div>

        {/* Keyboard Area */}
        <div className="bg-gray-200 p-2 pb-6">
           <div className="grid grid-cols-2 gap-2">
                <button 
                    onClick={() => handleCommand('resume', candidate.resume, 'TEXT')}
                    className="bg-white p-3 rounded-lg shadow-sm text-xs font-semibold text-gray-700 active:bg-blue-50 flex items-center justify-center gap-1">
                    <FileText size={14}/> رزومه
                </button>
                <button 
                    onClick={() => handleCommand('photo', candidate.photoUrl, 'IMAGE')}
                    className="bg-white p-3 rounded-lg shadow-sm text-xs font-semibold text-gray-700 active:bg-blue-50 flex items-center justify-center gap-1">
                    <User size={14}/> عکس و پروفایل
                </button>
                <button 
                    onClick={() => handleCommand('address', candidate.address, 'TEXT')}
                    className="bg-white p-3 rounded-lg shadow-sm text-xs font-semibold text-gray-700 active:bg-blue-50 flex items-center justify-center gap-1">
                    <MapPin size={14}/> آدرس ستاد
                </button>
                <button 
                    onClick={() => handleCommand('ideas', candidate.ideas, 'TEXT')}
                    className="bg-white p-3 rounded-lg shadow-sm text-xs font-semibold text-gray-700 active:bg-blue-50 flex items-center justify-center gap-1">
                    <Menu size={14}/> برنامه‌ها
                </button>
                <button 
                     onClick={() => handleCommand('voice', candidate.voiceUrl, 'AUDIO')}
                    className="bg-white p-3 rounded-lg shadow-sm text-xs font-semibold text-gray-700 active:bg-blue-50 flex items-center justify-center gap-1">
                    <Mic size={14}/> پیام صوتی
                </button>
           </div>
           
           {/* Input field simulation */}
           <div className="mt-2 flex items-center bg-white rounded-full px-3 py-2">
               <span className="text-gray-400 text-xs flex-1">پیام...</span>
               <Send size={16} className="text-[#517da2]"/>
           </div>
        </div>
      </div>
      <p className="mt-4 text-gray-500 text-sm font-medium">پیش‌نمایش بات تلگرام</p>
    </div>
  );
};

export default BotPreview;