import React from 'react';

interface ProviderIconProps {
  provider: string | null | undefined;
  className?: string;
  size?: number;
}

const ProviderIcon: React.FC<ProviderIconProps> = ({ provider, className = "", size = 16 }) => {
  const getIconPath = (name: string) => {
    const iconName = name.toLowerCase().replace(/_|\s/g, '');
    return `/src/assets/icons-providers/${iconName}.png`;
  };

  if (!provider || provider === 'unknown') {
    return null;
  }

  let normalizedProvider = provider.toLowerCase();
  if (normalizedProvider === 'youtube_music' || normalizedProvider === 'youtubemusic') {
    normalizedProvider = 'youtubemusic';
  } else if (normalizedProvider === 'amazon_music' || normalizedProvider === 'amazonmusic') {
    normalizedProvider = 'amazonmusic';
  } else if (normalizedProvider === 'apple_music' || normalizedProvider === 'applemusic') {
    normalizedProvider = 'applemusic';
  } else if (normalizedProvider === 'boomplay' || normalizedProvider === 'boomplaymusic') {
    normalizedProvider = 'boomplay';
  }

  return (
    <img 
      src={getIconPath(normalizedProvider)} 
      alt={provider}
      className={`inline-block object-contain ${className}`}
      style={{ width: size, height: size }}
      onError={(e) => {
        (e.target as HTMLImageElement).style.display = 'none';
      }}
    />
  );
};

export default ProviderIcon;
