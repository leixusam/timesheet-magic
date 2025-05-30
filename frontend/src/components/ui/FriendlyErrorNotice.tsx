import React from 'react';
// import { Button } from "@/components/ui/button"; // Removed to avoid import error
// import { AlertTriangle, HelpCircle, Trash2, UploadCloud } from 'lucide-react'; // Removed to avoid import error

interface FriendlyErrorNoticeProps {
  fileName: string;
  reportId: string;
  onTryDifferentFile: () => void;
  onNotifyMe: () => void; 
}

const FriendlyErrorNotice: React.FC<FriendlyErrorNoticeProps> = ({
  fileName,
  reportId,
  onTryDifferentFile,
  onNotifyMe,
}) => {
  // Basic button styling - can be replaced with actual Button component later
  const buttonBaseStyle = "px-4 py-2 border rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2";
  const primaryButtonStyle = `${buttonBaseStyle} text-white bg-blue-600 hover:bg-blue-700 focus:ring-blue-500`;
  const outlineButtonStyle = `${buttonBaseStyle} text-gray-700 bg-white border-gray-300 hover:bg-gray-50`;

  return (
    <div className="max-w-2xl mx-auto my-12 p-6 md:p-8 bg-white shadow-xl rounded-lg text-center">
      <div className="mx-auto flex items-center justify-center h-16 w-16 md:h-20 md:w-20 rounded-full bg-yellow-100 mb-5 md:mb-6">
        <span role="img" aria-label="Warning" className="text-3xl md:text-4xl">⚠️</span> {/* Placeholder for AlertTriangle icon */}
      </div>
      <h2 className="text-2xl md:text-3xl font-semibold text-gray-800 mb-3 md:mb-4">Upload Issue</h2>
      <p className="text-gray-600 mb-3 text-sm md:text-base">
        We encountered an issue processing your file, <span className="font-semibold">{fileName}</span>.
      </p>
      <p className="text-gray-600 mb-6 text-sm md:text-base">
        This can sometimes happen with very large or complex files, or formats we haven't fully optimized for yet. 
        Our team is always working to improve our system!
      </p>

      <div className="space-y-3 md:space-y-0 md:flex md:justify-center md:space-x-3">
        <button 
          onClick={onTryDifferentFile}
          className={`${outlineButtonStyle} w-full md:w-auto hover:border-blue-500 hover:text-blue-600`}
        >
          <span role="img" aria-label="Upload" className="mr-2">☁️</span> Try a Different File
        </button>
        
        <button 
          onClick={onNotifyMe} 
          className={`${outlineButtonStyle} w-full md:w-auto hover:border-green-500 hover:text-green-600`}
        >
          <span role="img" aria-label="Help" className="mr-2">📬</span> Notify Me When Ready
        </button>
      </div>
      
      <p className="mt-6 md:mt-8 text-xs md:text-sm text-gray-500">
        Report ID: {reportId}
      </p>
    </div>
  );
};

export default FriendlyErrorNotice; 