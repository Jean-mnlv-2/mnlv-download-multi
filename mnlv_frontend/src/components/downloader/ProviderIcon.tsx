import React from 'react';

// Importation des assets
import spotifyIcon from '../../assets/icons-providers/spotify.png';
import appleMusicIcon from '../../assets/icons-providers/applemusic.png';
import deezerIcon from '../../assets/icons-providers/deezer.png';
import soundcloudIcon from '../../assets/icons-providers/soundcloud.png';
import tidalIcon from '../../assets/icons-providers/tidal.png';
import amazonMusicIcon from '../../assets/icons-providers/amazonmusic.png';
import youtubeMusicIcon from '../../assets/icons-providers/youtubemusic.png';

export type ProviderType = 'spotify' | 'apple_music' | 'deezer' | 'soundcloud' | 'tidal' | 'amazon_music' | 'youtube_music' | string;

interface ProviderIconProps {
  provider: ProviderType | null;
  className?: string;
  size?: number;
}

const providerMap: Record<string, string> = {
  'spotify': spotifyIcon,
  'apple_music': appleMusicIcon,
  'apple': appleMusicIcon,
  'deezer': deezerIcon,
  'soundcloud': soundcloudIcon,
  'tidal': tidalIcon,
  'amazon_music': amazonMusicIcon,
  'amazon': amazonMusicIcon,
  'youtube_music': youtubeMusicIcon,
  'youtube': youtubeMusicIcon,
};

const ProviderIcon: React.FC<ProviderIconProps> = ({ provider, className = '', size = 20 }) => {
  if (!provider) return null;

  const normalizedProvider = provider.toLowerCase().replace(/\s/g, '_');
  const iconSrc = providerMap[normalizedProvider] || null;

  if (!iconSrc) {
    return null;
  }

  return (
    <img 
      src={iconSrc} 
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
