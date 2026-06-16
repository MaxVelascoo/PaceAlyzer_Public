'use client';
import Image from 'next/image';
import styles from './UserAvatar.module.css';

type Props = {
  avatarUrl?: string | null;
  initials: string;
  size?: number;
};

export default function UserAvatar({ avatarUrl, initials, size = 88 }: Props) {
  const radius = Math.round(size * 0.2); // border-radius proporcional

  return (
    <div className={styles.wrap} style={{ width: size, height: size }}>
      {avatarUrl ? (
        <Image
          src={avatarUrl}
          alt="Avatar"
          width={size}
          height={size}
          className={styles.img}
          style={{ borderRadius: radius }}
          unoptimized
        />
      ) : (
        <div
          className={styles.fallback}
          style={{ borderRadius: radius, fontSize: size * 0.28 }}
        >
          {initials}
        </div>
      )}
      <span className={styles.ring} style={{ borderRadius: radius + 8 }} aria-hidden />
    </div>
  );
}
