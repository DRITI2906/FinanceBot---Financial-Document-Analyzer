import React from 'react';
import { ExclamationTriangleIcon, ShieldCheckIcon, ExclamationCircleIcon } from '@heroicons/react/24/outline';

interface RiskBadgeProps {
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
}

const RiskBadge: React.FC<RiskBadgeProps> = ({ riskLevel, size = 'md', showIcon = true }) => {
  const getRiskConfig = (level: string) => {
    switch (level) {
      case 'low':
        return {
          label: 'Low Risk',
          className: 'risk-badge risk-low',
          icon: ShieldCheckIcon,
        };
      case 'medium':
        return {
          label: 'Medium Risk',
          className: 'risk-badge risk-medium',
          icon: ExclamationCircleIcon,
        };
      case 'high':
        return {
          label: 'High Risk',
          className: 'risk-badge risk-high',
          icon: ExclamationTriangleIcon,
        };
      case 'critical':
        return {
          label: 'Critical Risk',
          className: 'risk-badge risk-critical',
          icon: ExclamationTriangleIcon,
        };
      default:
        return {
          label: 'Unknown',
          className: 'risk-badge bg-gray-100 text-gray-800',
          icon: ShieldCheckIcon,
        };
    }
  };

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-0.5',
    lg: 'text-sm px-3 py-1',
  };

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-4 h-4',
  };

  const config = getRiskConfig(riskLevel);
  const Icon = config.icon;

  return (
    <span className={`${config.className} ${sizeClasses[size]} inline-flex items-center`}>
      {showIcon && <Icon className={`${iconSizes[size]} mr-1`} />}
      {config.label}
    </span>
  );
};

export default RiskBadge;
